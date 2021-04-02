'''
Bulk indexing of the Knowledge Base collections into ElasticSearch
'''

import sys
import json
from elasticsearch import Elasticsearch, helpers
from software_kb.common.arango_common import CommonArangoDB
from software_kb.kb.knowledge_base import knowledgeBase
import yaml
import argparse

settings_path = "software_kb/indexing/resources/settings.json";
mappings_path = "software_kb/indexing/resources/kb_mappings.json";
crossref_mappings_path = "software_kb/indexing/resources/crossref_mappings.json";

class Indexer(CommonArangoDB):

    def __init__(self, config_path="./config.yaml", reset=False):
        self.load_config(config_path)

        self.kb = knowledgeBase(config_path=config_path)

        self.es = Elasticsearch(
            [self.config["elasticsearch"]["host"]],
            port=self.config["elasticsearch"]["port"],
            sniff_on_start=True,
            # refresh nodes after a node fails to respond
            sniff_on_connection_fail=True,
            # and also every 60 seconds
            sniffer_timeout=60
        )
        #keepAlive: false,
        #suggestCompression: true

        # check if index exists
        if self.es.indices.exists(index=self.config['elasticsearch']['index_name']):
            # delete index if reset requested
            if reset:
                self.es.indices.delete(index=self.config['elasticsearch']['index_name'])

        if not self.es.indices.exists(index=self.config['elasticsearch']['index_name']):        
            # create index if not present with mappings

            # read setting and mappings json files 
            with open(settings_path) as json_file:
                settings_json = json.load(json_file)

            with open(mappings_path) as json_file:
                mappings_json = json.load(json_file)

            request_body = {
                "settings": settings_json,
                "mappings": mappings_json
            }
            self.es.indices.create(index=self.config['elasticsearch']['index_name'], body=request_body)

    def index(self):

        #self.index_collection(self.kb.documents, "documents")
        #print("number of indexed documents:", self.kb.documents.count())

        self.index_collection(self.kb.organizations, "organizations")
        print("number of indexed organizations:", self.kb.organizations.count())

        self.index_collection(self.kb.licenses, "licenses")
        print("number of indexed licenses:", self.kb.licenses.count())

        self.index_collection(self.kb.persons, "persons")
        print("number of indexed persons:", self.kb.persons.count())

        self.index_collection(self.kb.software, "software")        
        print("number of indexed software:", self.kb.software.count())

    def index_collection(self, collection, collection_name):
        page_size = self.config['elasticsearch']['batch_size']

        total_entries = collection.count()
        nb_pages = (total_entries // page_size)+1

        print("entries:", total_entries, ", nb. steps:", nb_pages)

        for page_rank in range(0,nb_pages):
            cursor = self.kb.db.aql.execute(
                'FOR doc IN ' + collection_name + ' LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) + ' RETURN doc', ttl=3600
            )
            
            actions = []
            for entity in cursor:
                # for the moment we don't index the document as such, but simplify it as preprocessing
                indexing_doc = self.flatten(entity, collection_name)
                action_doc = {}
                action_doc["_id"] = indexing_doc["id"]
                action_doc["_source"] = indexing_doc
                actions.append(action_doc)

                #res = self.es.index(index=self.config['elasticsearch']['index_name'], id=indexing_doc["id"], body=indexing_doc)
                #print(res)

            helpers.bulk(self.es, 
                actions, 
                index=self.config['elasticsearch']['index_name'], 
                chunk_size=500,
                refresh=True)
            
            '''
            self.es.indices.refresh(index=self.config['elasticsearch']['index_name'])
            print("results:")
            for doc in self.es.search(index=self.config['elasticsearch']['index_name'])['hits']['hits']:
                print(doc)
            '''

    def flatten(self, entity, collection_name):
        '''
        Simplify an entity representation into something flat and with simple fields for search
        and facetting purposes 
        '''
        doc = {}
        doc["id"] = entity["_key"]
        doc["collection"] = collection_name
        if isinstance(entity["labels"], str):
            doc["labels"] = entity["labels"]
        else:
            for key, value in entity["labels"].items():
                doc["labels"] = value["value"]
                break

        if collection_name == 'software':
            authors = []
            authors_full = []
            cursor = self.kb.db.aql.execute(
                'FOR actor IN actors \
                    FILTER actor._to == "' + entity["_id"] + '" \
                    RETURN actor._from')

            for person_id in cursor:
                # get the person object
                person_json = self.kb.kb_graph.vertex(person_id)
                if not person_json['labels'] in authors:
                    authors.append(person_json['labels'])
                    authors_full.append(person_json['labels'])

            doc['authors'] = authors
            doc['authors_full'] = authors_full

            # get contexts
            contexts = []
            cursor = self.kb.db.aql.execute(
                    'FOR mention IN citations '
                        + ' FILTER mention._to == "' + entity["_id"] + '"'
                        + ' LIMIT 0, 10'
                        + ' RETURN mention._id', full_count=True)
            total_results = 0
            stats = cursor.statistics()
            if 'fullCount' in stats:
                total_results = stats['fullCount']

            page_size = 1000
            nb_pages = (total_results // page_size)+1

            for page_rank in range(0, nb_pages):

                cursor = self.kb.db.aql.execute(
                    'FOR mention IN citations '
                        + ' FILTER mention._to == "' + entity["_id"] + '"'
                        + ' LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size)
                        + ' RETURN mention')

                for mention in cursor:
                    if "claims" in mention and "P7081" in mention["claims"]:
                        for the_context in mention["claims"]["P7081"]:
                            if "value" in the_context:
                                mention_context = the_context["value"]
                                if len(mention_context)>0:
                                    contexts.append(mention_context)

            if len(contexts) > 0:
                doc['contexts'] = contexts

            doc['number_mentions'] = len(contexts)

        if "claims" in entity:
            if "P275" in entity["claims"]:
                doc["licenses"] = []
                for the_value in entity["claims"]["P275"]:
                    doc["licenses"].append(the_value["value"]) 

            if "P277" in entity["claims"]:
                doc["programming_language"] = []
                doc["programming_language_class"] = []
                for the_value in entity["claims"]["P277"]:
                    converted_string = self.kb.naming_wikidata_string(the_value["value"])
                    doc["programming_language"].append(converted_string) 
                    doc["programming_language_class"].append(converted_string)

            # date should be added here

        if isinstance(entity["labels"], str):
            doc["all"] = entity["labels"]
        else:
            doc["all"] = ""
        if "descriptions" in entity and isinstance(entity["descriptions"], str) and len(entity["descriptions"])>0:
            doc["all"] += " " + entity["descriptions"]
            doc["descriptions"] = entity["descriptions"]
        if "summary" in entity and isinstance(entity["summary"], str) and len(entity["summary"])>0:
            doc["all"] += " " + entity["summary"]
            doc["summary"] = entity["summary"]

        if 'authors' in doc:
            for author in doc['authors']:
                doc["all"] += " " + author

        if "contexts" in doc:
            for context in doc["contexts"]:
                doc["all"] += " " + context

        return doc

if __name__ == '__main__':
    # stand alone mode, run the application
    parser = argparse.ArgumentParser(
        description="Create ElasticSearch index for the Software Knowledge Base search.")
    parser.add_argument("--config", default="./config.yaml", required=False, help="configuration file to be used")
    parser.add_argument("--reset", action="store_true", help="reset existing index and re-index all collections") 

    args = parser.parse_args()
    config_path = args.config
    to_reset = args.reset

    indexer = Indexer(config_path=config_path, reset=to_reset)
    indexer.index()
