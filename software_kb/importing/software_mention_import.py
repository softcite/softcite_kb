'''
    Import software mentions extracted by the Grobid module ourresearch/software-mentions

    This is realized via the MongoDB JSON export where every mention objects are written. Three collections
    are available: mentions, documents (documents where the mention is extracted) and references 
    (bibliographical references part of the context and attached to the extracted mentioned software)

'''

import requests
import argparse
import json
from software_kb.importing.harvester import Harvester
from arango import ArangoClient
import re
import os
import gzip

class Software_mention_import(Harvester):

    database_name = "mentions"
    blacklist_files = [ "data/mentions/blacklists/cord-19.blacklist.software-mentions.txt" ]

    def __init__(self, config_path="./config.yaml"):
        self.load_config(config_path)

        # create database and collection
        if not self.sys_db.has_database(self.database_name):
            self.sys_db.create_database(self.database_name)

        self.db = self.client.db(self.database_name, username=self.config['arangodb']['arango_user'], password=self.config['arangodb']['arango_pwd'])

        if not self.db.has_collection('annotations'):
            self.annotations = self.db.create_collection('annotations')
            # we add a hash index on the document identifier
            self.index_document = self.annotations.add_hash_index(fields=['document.$oid'], unique=False, sparse=False)
        else:
            self.annotations = self.db.collection('annotations')

        if not self.db.has_collection('documents'):
            self.documents = self.db.create_collection('documents')
        else:
            self.documents = self.db.collection('documents')

        if not self.db.has_collection('references'):
            self.references = self.db.create_collection('references')
        else:
            self.references = self.db.collection('references')

        # blacklist
        self.blacklist = []
        for black_file in self.blacklist_files:
            if not os.path.isfile(black_file): 
                continue
            with open(black_file) as fp:
                for line in fp:
                    line = line.strip()
                    if len(line)>0 and not line in self.blacklist and not line.startswith("#"):
                        self.blacklist.append(line)

    def import_mentions(self, mongoExportPath, reset=False, tags=None):
        '''
        We use the result of mongoexport, one JSON per line, with one file per collection.
        This can be incremental, loading different set of mentions extraction dumps from different sources/set of PDF. 
        ''' 
        if reset:
            # TBD: we might want to prompt a confirmation, because it might be very destructive!
            self.db.delete_collection('annotations')
            self.annotations = self.db.create_collection('annotations')
            self.index_document = self.annotations.add_hash_index(fields=['document.$oid'], unique=False, sparse=False)

            self.db.delete_collection('documents')
            self.documents = self.db.create_collection('documents')

            self.db.delete_collection('references')
            self.references = self.db.create_collection('references')

        # import JSON collections
        for thefile in os.listdir(mongoExportPath):
            if thefile.find("annotations") != -1:
                if thefile.endswith(".gz"):
                    with gzip.open(os.path.join(mongoExportPath, thefile), 'rb') as fjson:
                        for line in fjson:
                            self._load_json(line, self.annotations, "annotations", tags=tags)
                else:
                    with open(os.path.join(mongoExportPath, thefile)) as fjson:
                        for line in fjson:
                            self._load_json(line, self.annotations, "annotations", tags=tags)
            elif thefile.find("documents") != -1:
                if thefile.endswith(".gz"):
                    with gzip.open(os.path.join(mongoExportPath, thefile), 'rb') as fjson:
                        for line in fjson:
                            self._load_json(line, self.documents, "documents", tags=tags)
                else:
                    with open(os.path.join(mongoExportPath, thefile)) as fjson:
                        for line in fjson:
                            self._load_json(line, self.documents, "documents", tags=tags)
            elif thefile.find("references") != -1:
                if thefile.endswith(".gz"):
                    with gzip.open(os.path.join(mongoExportPath, thefile), 'rb') as fjson:
                        for line in fjson:
                            self._load_json(line, self.references, "references", tags=tags)
                else:
                    with open(os.path.join(mongoExportPath, thefile)) as fjson:
                        for line in fjson:
                            self._load_json(line, self.references, "references", tags=tags)
            else:
                print("File skipped:", os.path.join(mongoExportPath, thefile))

    def _load_json(self, json_string, collection, collection_name, tags=None):
        '''
        we use "$oid" under _id as key for the entry
        '''
        try:
            json_object = json.loads(json_string.decode('utf-8'))
            local_id = json_object['_id']
            local_id = local_id['$oid']
            json_object['_id'] = collection_name + "/" + local_id
            # check blacklist
            if collection_name == "annotations":
                if "software-name" in json_object:
                    term = json_object["software-name"]["normalizedForm"]
                    if term in self.blacklist or term.find("SARS") != -1 or _is_number(term):
                        return
            # insert
            if not collection.has(json_object['_id']):
                json_object['tenants'] = tags
                collection.insert(json_object)
        except:
            print("failed to ingest json input:", json_string)

    def get_document_annotations(self, document_id):
        '''
        Return the annotations for a given document, with page dimentions. This is similar
        as what the softcite software mention recognizer is returning and allows to
        visualize the mentions from the KB only. 
        '''
        result = {}

        # first get document record for page dimentions
        doc_record = self.documents.get('documents/' + document_id)

        if doc_record == None or not 'pages' in doc_record:
            return result

        result['pages'] = doc_record['pages']
        result['md5'] = doc_record['md5']
        result['mentions'] = []
        result['references'] = []

        # retrieve all the annotations for this document
        cursor = self.db.aql.execute(
            'FOR annotation IN annotations FILTER annotation["document"]["$oid"] == "' + document_id + '" RETURN annotation', ttl=3600
        )

        for annotation in cursor:
            del annotation['document']
            result['mentions'].append(annotation)

        # retrieve the references information
        cursor = self.db.aql.execute(
            'FOR reference IN references FILTER reference["document"]["$oid"] == "' + document_id + '" RETURN reference', ttl=3600
        )

        for reference in cursor:
            del reference['document']
            result['references'].append(reference)


        return result

def _is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Import collection of automatically extracted software mention")
    parser.add_argument("mongoExportPath", default=None, help="path to the directory with MongoDB JSON export containing the software mentions") 
    parser.add_argument("--config", default="./config.yaml", help="path to the config file, default is ./config.yaml") 
    parser.add_argument("--reset", action="store_true", help="reset existing collections and re-import all software mention records") 
    parser.add_argument("--tag", default=None, nargs='*', help="one or several labels to be associated to the loaded document, e.g. name of collection")

    args = parser.parse_args()
    config_path = args.config
    mongoExportPath = args.mongoExportPath
    to_reset = args.reset
    tags = args.tag

    if mongoExportPath is not None:
        local_harvester = Software_mention_import(config_path=config_path)
        local_harvester.import_mentions(mongoExportPath, reset=to_reset, tags=tags)
    else:
        print("No MongoDB export directory path indicated")
