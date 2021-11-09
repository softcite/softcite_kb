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
import datetime
from tqdm import tqdm

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

        # document are not indexed for search at the present time
        #self.index_collection(self.kb.documents, "documents")
        #print("number of indexed documents:", self.kb.documents.count())

        print("\nnumber of organization entities to index:", self.kb.organizations.count())
        self.index_collection(self.kb.organizations, "organizations")
        
        print("\nnumber of license entities to index:", self.kb.licenses.count())
        self.index_collection(self.kb.licenses, "licenses")
        
        print("\nnumber of person entities to index:", self.kb.persons.count())
        self.index_collection(self.kb.persons, "persons")
        
        print("\nnumber of software entities to index:", self.kb.software.count())
        self.index_collection(self.kb.software, "software")        
        

    def index_collection(self, collection, collection_name):
        page_size = self.config['elasticsearch']['batch_size']

        total_entries = collection.count()
        nb_pages = (total_entries // page_size)+1

        print("entries:", total_entries, ", nb. steps:", nb_pages)

        for page_rank in tqdm(range(0,nb_pages)):
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
            authors_id = []
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
                    if "id" in person_json:
                        authors_id.append(person_json['id'])

            doc['authors'] = authors
            doc['authors_full'] = authors_full
            doc['authors_id'] = authors_id

            # get contexts
            contexts = []
            documents = []
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

            timeline_mentions = {}
            timeline_documents = {}

            for page_rank in range(0, nb_pages):

                cursor = self.kb.db.aql.execute(
                    'FOR mention IN citations '
                        + ' FILTER mention._to == "' + entity["_id"] + '"'
                        + ' LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size)
                        + ' RETURN mention')

                year = None 
                previous_doc_id = None 
                for mention in cursor:
                    if "claims" in mention and "P7081" in mention["claims"]:
                        for the_context in mention["claims"]["P7081"]:
                            if "value" in the_context:
                                mention_context = the_context["value"]
                                if len(mention_context)>0:
                                    contexts.append(mention_context)
                                    if mention["_from"] != previous_doc_id:
                                        year = self.extract_year(mention["_from"])
                                        previous_doc_id = mention["_from"]
                                    if year != None:
                                        if year in timeline_mentions:
                                            timeline_mentions[year] += 1
                                        else:
                                            timeline_mentions[year] = 1
                                    if not mention["_from"] in documents:
                                        documents.append(mention["_from"])
                                        if year != None:
                                            if year in timeline_documents:
                                                timeline_documents[year] += 1
                                            else:
                                                timeline_documents[year] = 1

            if len(contexts) > 0:
                doc['contexts'] = contexts

            # number of mentions for software 
            doc['number_mentions'] = len(contexts)

            # number of citing documents for software 
            doc['number_documents'] = len(documents)

            # time distribution of mentions
            timeline_array = []

            for key in timeline_documents:
                timeline_array.append( {"key": key, "doc_count": timeline_documents[key], "mention_count": timeline_mentions[key] } );
            doc['timeline'] = timeline_array

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

                # date added here, for software we use inception date P571
                if "P571" in entity["claims"]:
                    for the_value in entity["claims"]["P571"]:
                        if "time" in the_value:
                            time_expression = the_value["time"]
                            # format "+2011-00-00T00:00:00Z" into yyyy-MM-dd 
                            time_expression = time_expression.replace('+', '')
                            ind = time_expression.find("T")
                            if ind != -1:
                                time_expression = time_expression[:ind]
                            doc["date"] = time_expression

        if collection_name == 'organizations':
            # add location information - at this point it's simply country ISO 3166 code (2 characters) 
            # country property is P17
            if "claims" in entity:
                if "P17" in entity["claims"]:
                    for the_value in entity["claims"]["P17"]:
                        converted_string = self.kb.naming_wikidata_string(the_value["value"])
                        doc["country"] = converted_string
                        break

            # add corresponding number mentions: mentions of a software the organization has indirect authorship or funding


        if collection_name == 'persons':
            # add corresponding number mentions: mentions of a software the person has authorship) 
            # get contexts of software co-authored by the person
            contexts = []
            documents = []

            cursor = self.kb.db.aql.execute(
                'FOR actor IN actors '
                    + ' FILTER actor._from == "' + entity["_id"] + '" && (SPLIT(actor._to, "/", 1)[0]) IN ["software"] '
                    + ' FOR mention IN citations '
                    + '    FILTER mention._to == actor._to '
                    + '    LIMIT 0, 10'
                    + '    RETURN DISTINCT mention._id ', full_count=True)

            total_results = 0
            stats = cursor.statistics()
            if 'fullCount' in stats:
                total_results = stats['fullCount']

            page_size = 1000
            nb_pages = (total_results // page_size)+1

            for page_rank in range(0, nb_pages):

                cursor = self.kb.db.aql.execute(
                    'FOR actor IN actors '
                    + ' FILTER actor._from == "' + entity["_id"] + '" && (SPLIT(actor._to, "/", 1)[0]) IN ["software"] '
                    + ' FOR mention IN citations '
                    + '    FILTER mention._to == actor._to '
                    + '    LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size)
                    + '    RETURN DISTINCT mention ')

                for mention in cursor:
                    if "claims" in mention and "P7081" in mention["claims"]:
                        for the_context in mention["claims"]["P7081"]:
                            if "value" in the_context:
                                mention_context = the_context["value"]
                                if len(mention_context)>0:
                                    contexts.append(mention_context)
                                    if not mention["_from"] in documents:
                                        documents.append(mention["_from"])

            if len(contexts) > 0:
                doc['contexts'] = contexts

            # number of mentions for software 
            doc['number_mentions'] = len(contexts)

            # number of citing documents for software 
            doc['number_documents'] = len(documents)

        #if collection_name == 'licenses':
        # add corresponding software usage number: number of software using this license

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

    def extract_year(self, document_id):
        '''
        Extract the publication year of a document (earliest publication date), if available
        '''
        document_entity_item = self.kb.documents.get(document_id)
        year = None
        if "metadata" in document_entity_item:
            if "issued" in document_entity_item["metadata"]:
                year = document_entity_item["metadata"]["issued"]["date-parts"][0][0]
            elif "published-online" in document_entity_item["metadata"]:
                year = document_entity_item["metadata"]["published-online"]["date-parts"][0][0]
        if year != None:
            try:
                #local_date = datetime.datetime(int(year),1,1) 
                #return int((local_date - datetime.datetime(1970, 1, 1)).total_seconds())
                return int(year)
            except:
                return None
        else:
            return None

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
