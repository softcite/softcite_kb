'''
    Import software mentions extracted by the Grobid module ourresearch/software-mentions

    This is realized via the MongoDB JSON export where every mention objects are written. Three collections
    are available: mentions, documents (documents where the mention is extracted) and references 
    (bibliographical references part of the context and attached to the extracted mentioned software)

'''

import requests
import argparse
import json
from harvester import Harvester
from arango import ArangoClient
import re
import os
import gzip

class Software_mention_import(Harvester):

    database_name = "mentions"

    def __init__(self, config_path="./config.json"):
        self.load_config(config_path)

        # create database and collection
        if not self.sys_db.has_database(self.database_name):
            self.sys_db.create_database(self.database_name)

        self.db = self.client.db(self.database_name, username=self.config['arango_user'], password=self.config['arango_pwd'])

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

    def import_mentions(self, mongoExportPath, reset=False):
        '''
        we use the result of mongoexport, one JSON per line, with one file per collection
        ''' 
        if reset:
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
                            self._load_json(line, self.annotations, "annotations")
                else:
                    with open(os.path.join(mongoExportPath, thefile)) as fjson:
                        for line in fjson:
                            self._load_json(line, self.annotations, "annotations")
            elif thefile.find("documents") != -1:
                if thefile.endswith(".gz"):
                    with gzip.open(os.path.join(mongoExportPath, thefile), 'rb') as fjson:
                        for line in fjson:
                            self._load_json(line, self.documents, "documents")
                else:
                    with open(os.path.join(mongoExportPath, thefile)) as fjson:
                        for line in fjson:
                            self._load_json(line, self.documents, "documents")
            elif thefile.find("references") != -1:
                if thefile.endswith(".gz"):
                    with gzip.open(os.path.join(mongoExportPath, thefile), 'rb') as fjson:
                        for line in fjson:
                            self._load_json(line, self.references, "references")
                else:
                    with open(os.path.join(mongoExportPath, thefile)) as fjson:
                        for line in fjson:
                            self._load_json(line, self.references, "references")
            else:
                print("File skipped:", os.path.joint(mongoExportPath, thefile))

    def _load_json(self, json_string, collection, collection_name):
        '''
        we use "$oid" under _id as key for the entry
        '''
        try:
            json_object = json.loads(json_string.decode('utf-8'))
            local_id = json_object['_id']
            local_id = local_id['$oid']
            json_object['_id'] = collection_name + "/" + local_id
            # insert
            if not collection.has(json_object['_id']):
                collection.insert(json_object)
        except:
            print("failed to ingest json input:", json_string)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Import collection of automatically extracted software mention")
    parser.add_argument("mongoExportPath", default=None, help="path to the directory with MongoDB JSON export containing the software mentions") 
    parser.add_argument("--config", default="./config.json", help="path to the config file, default is ./config.json") 
    parser.add_argument("--reset", action="store_true", help="reset existing collections and re-import all software mention records") 

    args = parser.parse_args()
    config_path = args.config
    mongoExportPath = args.mongoExportPath
    to_reset = args.reset

    if mongoExportPath is not None:
        local_harvester = Software_mention_import(config_path=config_path)
        local_harvester.import_mentions(mongoExportPath, reset=to_reset)
    else:
        print("No MongoDB export directory path indicated")

