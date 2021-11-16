'''
Actual Knowledge Base level with deduplicated/disambiguated entities coming from the staging area. 
No new entities and relations are created at this level, they are imported from the staging area and conflated. 

This database is used by the service API and appropiate index are built for this purpose.  
'''

import os
import sys
import json
from arango import ArangoClient
from software_kb.common.arango_common import CommonArangoDB, _get_entity_from_wikidata
from software_kb.merging.populate_staging_area import StagingArea, _project_entity_id_collection
from software_kb.common.arango_common import simplify_entity
import argparse
from tqdm import tqdm
import requests
from requests.exceptions import HTTPError
import logging
import logging.handlers

class knowledgeBase(CommonArangoDB):

    # vertex collections 
    software = None
    persons = None
    organizations = None
    documents = None
    licenses = None

    # edge collections 
    citations = None
    references = None
    actors = None
    copyrights = None
    dependencies = None
    funding = None

    database_name = "kb"
    graph_name = "kb_graph"

    # for mapping Wikidata property to person roles
    relator_map = None

    # for displaying source annotations on PDF easily, an handle to the software mention import database
    software_mentions = None

    # keep track of the original config file used to initialize the KB
    config_path = None

    def __init__(self, config_path="./config.yaml"):
        self.config_path = config_path
        self.load_config(config_path)
        self.init_naming()

        # create database if it doesn't exist
        if not self.sys_db.has_database(self.database_name):
            self.sys_db.create_database(self.database_name)

        self.db = self.client.db(self.database_name, username=self.config['arangodb']['arango_user'], password=self.config['arangodb']['arango_pwd'])

        if not self.db.has_collection('cache'):
            self.cache = self.db.create_collection('cache')
        else:
            self.cache = self.db.collection('cache')

        if self.db.has_graph(self.graph_name):
            self.kb_graph = self.db.graph(self.graph_name)
        else:
            self.kb_graph = self.db.create_graph(self.graph_name)

        # init vertex collections if they don't exist
        if not self.kb_graph.has_vertex_collection('software'):
            self.software = self.kb_graph.create_vertex_collection('software')
        else:
            self.software = self.kb_graph.vertex_collection('software')

        if not self.kb_graph.has_vertex_collection('persons'):
            self.persons = self.kb_graph.create_vertex_collection('persons')
        else:
            self.persons = self.kb_graph.vertex_collection('persons')

        if not self.kb_graph.has_vertex_collection('organizations'):
            self.organizations = self.kb_graph.create_vertex_collection('organizations')
        else:
            self.organizations = self.kb_graph.vertex_collection('organizations')

        if not self.kb_graph.has_vertex_collection('documents'):
            self.documents = self.kb_graph.create_vertex_collection('documents')
        else:
            self.documents = self.kb_graph.vertex_collection('documents')

        if not self.kb_graph.has_vertex_collection('licenses'):
            self.licenses = self.kb_graph.create_vertex_collection('licenses')
        else:
            self.licenses = self.kb_graph.vertex_collection('licenses')

        # init edge collections if they don't exist
        if not self.kb_graph.has_edge_collection('citations'):
            self.citations = self.kb_graph.create_edge_definition(
                edge_collection='citations',
                from_vertex_collections=['documents'],
                to_vertex_collections=['software']
            )
        else:
            self.citations = self.kb_graph.edge_collection('citations')

        if not self.kb_graph.has_edge_collection('references'):
            self.references = self.kb_graph.create_edge_definition(
                edge_collection='references',
                from_vertex_collections=['software', 'documents'],
                to_vertex_collections=['software', 'documents']
            )
            self.index_referring_software = self.references.add_hash_index(fields=['index_software'], unique=False, sparse=False)
        else:
            self.references = self.kb_graph.edge_collection('references')

        if not self.kb_graph.has_edge_collection('actors'):
            self.actors = self.kb_graph.create_edge_definition(
                edge_collection='actors',
                from_vertex_collections=['persons'],
                to_vertex_collections=['software', 'documents']
            )
        else:
            self.actors = self.kb_graph.edge_collection('actors')

        if not self.kb_graph.has_edge_collection('copyrights'):
            self.copyrights = self.kb_graph.create_edge_definition(
                edge_collection='copyrights',
                from_vertex_collections=['persons', 'organizations'],
                to_vertex_collections=['software']
            )
        else:
            self.copyrights = self.kb_graph.edge_collection('copyrights')

        if not self.kb_graph.has_edge_collection('dependencies'):
            self.dependencies = self.kb_graph.create_edge_definition(
                edge_collection='dependencies',
                from_vertex_collections=['software'],
                to_vertex_collections=['software']
            )
        else:
            self.dependencies = self.kb_graph.edge_collection('dependencies')

        if not self.kb_graph.has_edge_collection('funding'):
            self.funding = self.kb_graph.create_edge_definition(
                edge_collection='funding',
                from_vertex_collections=['software', "documents"],
                to_vertex_collections=['organizations']
            )
        else:
            self.funding = self.kb_graph.edge_collection('funding')


    def reset(self):
        # edge collections
        if self.kb_graph.has_edge_collection('citations'):
            self.kb_graph.delete_edge_definition('citations', purge=True)

        if self.kb_graph.has_edge_collection('references'):
            self.kb_graph.delete_edge_definition('references', purge=True)

        if self.kb_graph.has_edge_collection('actors'):
            self.kb_graph.delete_edge_definition('actors', purge=True)

        if self.kb_graph.has_edge_collection('copyrights'):
            self.kb_graph.delete_edge_definition('copyrights', purge=True)

        if self.kb_graph.has_edge_collection('dependencies'):
            self.kb_graph.delete_edge_definition('dependencies', purge=True)

        if self.kb_graph.has_edge_collection('funding'):
            self.kb_graph.delete_edge_definition('funding', purge=True)

        # vertex collections
        if self.kb_graph.has_vertex_collection('software'):
            self.kb_graph.delete_vertex_collection('software', purge=True)

        if self.kb_graph.has_vertex_collection('persons'):
            self.kb_graph.delete_vertex_collection('persons', purge=True)

        if self.kb_graph.has_vertex_collection('organizations'):
            self.kb_graph.delete_vertex_collection('organizations', purge=True)

        if self.kb_graph.has_vertex_collection('documents'):
            self.kb_graph.delete_vertex_collection('documents', purge=True)

        if self.kb_graph.has_vertex_collection('licenses'):
            self.kb_graph.delete_vertex_collection('licenses', purge=True)

        self.software = self.kb_graph.create_vertex_collection('software')
        self.persons = self.kb_graph.create_vertex_collection('persons')
        self.organizations = self.kb_graph.create_vertex_collection('organizations')
        self.documents = self.kb_graph.create_vertex_collection('documents')
        self.licenses = self.kb_graph.create_vertex_collection('licenses')

        self.citations = self.kb_graph.create_edge_definition(
                edge_collection='citations',
                from_vertex_collections=['documents'],
                to_vertex_collections=['software']
            )

        self.references = self.kb_graph.create_edge_definition(
                edge_collection='references',
                from_vertex_collections=['software', 'documents'],
                to_vertex_collections=['software', 'documents']
            )
        self.index_referring_software = self.references.add_hash_index(fields=['index_software'], unique=False, sparse=False)

        self.actors = self.kb_graph.create_edge_definition(
                edge_collection='actors',
                from_vertex_collections=['persons'],
                to_vertex_collections=['software', 'documents']
            )

        self.copyrights = self.kb_graph.create_edge_definition(
                edge_collection='copyrights',
                from_vertex_collections=['persons', 'organizations'],
                to_vertex_collections=['software']
            )

        self.dependencies = self.kb_graph.create_edge_definition(
                edge_collection='dependencies',
                from_vertex_collections=['software'],
                to_vertex_collections=['software']
            )

        self.funding = self.kb_graph.create_edge_definition(
                edge_collection='funding',
                from_vertex_collections=['software', "documents"],
                to_vertex_collections=['organizations']
            )

    def init(self, config_path="./config.yaml", reset=False):
        if reset:
            self.reset()

        self.init_collections(config_path=config_path)
        self.set_up_relations()

        # the following import additional missing Wikidata entities via the Wikdata REST API 
        self.complete_entities()

    def init_collections(self, config_path="./config.yaml"):

        stagingArea = StagingArea(config_path=config_path)

        self.init_collection(stagingArea, stagingArea.documents, "documents")
        print("number of loaded documents after deduplication:", self.documents.count())

        self.init_collection(stagingArea, stagingArea.organizations, "organizations")
        print("number of loaded organizations after deduplication:", self.organizations.count())

        self.init_collection(stagingArea, stagingArea.licenses, "licenses")
        print("number of loaded licenses after deduplication:", self.licenses.count())

        self.init_collection(stagingArea, stagingArea.persons, "persons")
        print("number of loaded persons after deduplication:", self.persons.count())

        self.init_collection(stagingArea, stagingArea.software, "software")        
        print("number of loaded software after deduplication:", self.software.count())

    def init_collection(self, stagingArea, collection_staging_area, collection_name):

        print("\n" + collection_name + " kb loading")
        total_results = collection_staging_area.count()
        page_size = 1000
        nb_pages = (total_results // page_size)+1

        print("total", collection_name + ":", total_results, ", nb. steps:", nb_pages)

        for page_rank in tqdm(range(0, nb_pages)):

            cursor = stagingArea.db.aql.execute(
                'FOR doc IN ' + collection_name + ' LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) + ' RETURN doc', ttl=3600
            )
            
            for entity in cursor:
                # init count to 1 at source levels
                entity = _init_count(entity)

                # check if the entry shall be merged
                if stagingArea.staging_graph.has_vertex("merging_entities/" + entity['_key']):
                    # this entity has to be merged with other ones of its merging group
                    merging_entity_item = stagingArea.merging_entities.get("merging_entities/" + entity['_key'])
                    merging_list_id = merging_entity_item['list_id']

                    # get the list content
                    merging_list_item = stagingArea.merging_lists.get(merging_list_id)
                    merging_list = merging_list_item['data']

                    # we have to check the rank of the entity in the list (of entity _id), only the first one is canonical
                    rank = _index(merging_list, entity['_id'])
                    if rank != None and rank == 0:
                        # merge
                        start = True 
                        for local_id in merging_list:
                            if start:
                                start = False
                                merged_entity = collection_staging_area.get(local_id)
                                continue
                            to_merge_entity = collection_staging_area.get(local_id)
                            merged_entity = self.aggregate_with_merge(merged_entity, to_merge_entity)
                        if not self.kb_graph.has_vertex(merged_entity['_id']):
                            self.normalize_entity(merged_entity)
                            self.kb_graph.insert_vertex(collection_name, merged_entity)
                    else:
                        continue
                else:
                    # no merging involved with this entity, we add it to the KB and continue
                    if not self.kb_graph.has_vertex(entity['_id']):
                        self.normalize_entity(entity)
                        self.kb_graph.insert_vertex(collection_name, entity)

    def set_up_relations(self):
        '''
        Load relations from staging area and update them based on merged vertex.
        '''
        stagingArea = StagingArea(config_path=config_path)

        self.set_up_relation(stagingArea, stagingArea.actors, "actors")
        self.set_up_relation(stagingArea, stagingArea.citations, "citations")
        self.set_up_relation(stagingArea, stagingArea.copyrights, "copyrights")
        self.set_up_relation(stagingArea, stagingArea.dependencies, "dependencies")
        self.set_up_relation(stagingArea, stagingArea.funding, "funding")
        self.set_up_relation(stagingArea, stagingArea.references, "references")

    def set_up_relation(self, stagingArea, collection_staging_area, edge_collection_name):

        print("\n" + edge_collection_name + " relations kb loading")

        total_results = collection_staging_area.count()
        page_size = 1000
        nb_pages = (total_results // page_size)+1

        print("total " + edge_collection_name + " edges:", total_results, ", nb. steps:", nb_pages)

        for page_rank in tqdm(range(0, nb_pages)):

            cursor = stagingArea.db.aql.execute(
                'FOR doc IN ' + edge_collection_name + ' LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) + ' RETURN doc', ttl=3600
            )

            for entity in cursor:
                # init count to 1 at source levels
                entity = _init_count(entity)

                # check "from" and "to" vertex
                from_entity_id = entity["_from"]
                to_entity_id = entity["_to"]

                # if vertex does not exist, find the list and the canonical vertex where it has been merged
                if not self.kb_graph.has_vertex(from_entity_id):
                    from_merged_entity_id = _project_entity_id_collection(from_entity_id, "merging_entities")
                    merging_entity_item = stagingArea.merging_entities.get(from_merged_entity_id)
                    if merging_entity_item != None:
                        merging_list_id = merging_entity_item['list_id']
                        merging_list_item = stagingArea.merging_lists.get(merging_list_id)
                        merging_list = merging_list_item['data']
                        new_from_entity_id = merging_list[0]
                        entity["_from"] = new_from_entity_id

                if not self.kb_graph.has_vertex(to_entity_id):
                    to_merged_entity_id = _project_entity_id_collection(to_entity_id, "merging_entities")
                    merging_entity_item = stagingArea.merging_entities.get(to_merged_entity_id)
                    if merging_entity_item != None:
                        merging_list_id = merging_entity_item['list_id']
                        merging_list_item = stagingArea.merging_lists.get(merging_list_id)
                        merging_list = merging_list_item['data']
                        new_to_entity_id = merging_list[0]
                        entity["_to"] = new_to_entity_id

                # in the case of reference, we might have a software identifier in the "P2860" property to keep track
                # of the mentioned software in the bibliographical reference context - this identifier need to be
                # updated as well wrt. to deduplication, e.g.:
                '''
                "claims": {
                    "P2860": [
                      {
                        "value": "software/fa553d69b7364767a13caa4c",
                        "datatype": "external-id",
                '''
                if edge_collection_name == "references" and "claims" in entity and "P2860" in entity["claims"]:
                    for the_value in entity["claims"]["P2860"]:
                        if "value" in the_value:
                            local_software_id = the_value["value"]
                            if not self.kb_graph.has_vertex(local_software_id):
                                merged_entity_id = _project_entity_id_collection(local_software_id, "merging_entities")
                                merging_entity_item = stagingArea.merging_entities.get(merged_entity_id)
                                if merging_entity_item != None:
                                    merging_list_id = merging_entity_item['list_id']
                                    merging_list_item = stagingArea.merging_lists.get(merging_list_id)
                                    merging_list = merging_list_item['data']
                                    new_entity_id = merging_list[0]
                                    the_value["value"] = new_entity_id
                                    entity['index_software'] = new_entity_id
                                    # only one software associated to a reference in a software citation context
                                    break

                # update relation with merged vertex
                if not self.kb_graph.has_edge(entity['_id']):
                    self.kb_graph.insert_edge(edge_collection_name, entity)

    def complete_entities(self):
        ''' 
        The mentions introduce entities via disambiguisation, which might have been imported via software
        instance properties. In order to import only safe missing entities, we exploit the count information
        after merging to compute a probability. If this probability is high enough, we add the wikidata entity
        in the import list. 
        '''

        software_list = []
        with open("data/resources/software.wikidata.entities", "rt") as fp:
            for line in fp:
                software_list.append(line.rstrip())

        total_results = self.software.count()
        page_size = 1000
        nb_pages = (total_results // page_size)+1

        print("Quality check on software entity disambiguation...")

        for page_rank in tqdm(range(0, nb_pages)):

            cursor = self.db.aql.execute(
                'FOR doc IN software LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) + ' RETURN doc', ttl=3600
            )
            
            for soft in cursor:
                # get mention count
                contexts = []
                cursor = self.db.aql.execute(
                    'FOR mention IN citations '
                        + ' FILTER mention._to == "' + soft["_id"] + '"'
                        + ' RETURN mention._id', full_count=True)
                total_mentions = 0
                stats = cursor.statistics()
                if 'fullCount' in stats:
                    total_mentions = stats['fullCount']

                # check the disambiguated entity and the number of disambiguation against the total number of mentions
                count = 0
                entity_id = None
                if "claims" in soft:
                    if "P460" in soft["claims"]:
                        for the_value in soft["claims"]["P460"]:
                            if isinstance(the_value["value"], str) and the_value["value"].startswith("Q"):
                                local_entity_id = the_value["value"]
                                if "references" in the_value and "count" in the_value["references"][0]["P248"]:
                                    local_count = the_value["references"][0]["P248"]["count"]

                                    if local_count > count:
                                        count = local_count
                                        entity_id = local_entity_id

                if entity_id == None:
                    continue

                # if no summary but a wikidata entity, try to get one via entity-fishing which has extracted summaries from
                # the corresponding Wikipedia English pages
                new_summary = None
                if not "summary" in soft or len(soft["summary"]) == 0:
                    local_summary = self.get_summary(entity_id)
                    if local_summary != None:
                        new_summary = local_summary

                if total_mentions < 10: 
                    continue

                if count <= 1:
                    continue

                if count > total_mentions/2:
                    # valid entity... keep track of the entity if not imported yet
                    if not entity_id in software_list:
                        software_list.append(entity_id)

                    # update summary
                    if new_summary != None:
                        soft["summary"] = new_summary

                    # to immediatly integrate this missing entity, we can retrieve it online and merge it 
                    entity_json = _get_entity_from_wikidata(entity_id)
                    if entity_json != None:
                        soft = self.aggregate_with_merge(soft, entity_json)

                    # finally update the software entity in the KB
                    self.kb_graph.update_vertex(soft)

        # update entity list
        with open("data/resources/software.wikidata.entities2", "wt") as fp:
            for wikipedia_entity_id in software_list:
                fp.write(wikipedia_entity_id)
                fp.write("\n")

    def get_summary(self, wikidata_id):
        nerd_url = self.config["entity-fishing"]["entity_fishing_protocol"] + "://" + self.config["entity-fishing"]["entity_fishing_host"]
        if self.config["entity-fishing"]["entity_fishing_port"] != None and self.config["entity-fishing"]["entity_fishing_port"] != 0:
             nerd_url += ":" + self.config["entity-fishing"]["entity_fishing_port"]

        nerd_url += "/service/kb/concept/" + wikidata_id
        result_json = None
        try:
            response = requests.get(nerd_url)
            response.raise_for_status()
            result_json = response.json()
        except HTTPError as http_err:
            print('HTTP error occurred:', http_err)
        except Exception as err:
            print('Error occurred:', err)

        if result_json == None:
            return None

        summary = None
        if "definitions" in result_json:
            for definition_object in result_json["definitions"]:
                if "lang" in definition_object and definition_object["lang"] == 'en' and "definition" in definition_object:
                    local_summary = definition_object["definition"]
                    if len(local_summary) > 10:
                        summary = local_summary
                        break
        return summary

    def relator_role_wikidata(self, wikidata_property):
        '''
        Map a Wikidata property to a role dictionary with relator information (MARC/CRAN, codemeta) on person role
        '''
        if self.relator_map == None:
            # load relator resource file and create inverse wikidata property map
            relator_file = os.path.join("data", "resources", "relator_code_cran.json")
            if not os.path.isfile(relator_file): 
                print("Error when loading relator code:", relator_file)
                return None

            self.relator_map = {}
            with open(relator_file) as relator_f:
                relator_code_cran = json.load(relator_f)
                for key in relator_code_cran:
                    if "wikidata" in relator_code_cran[key]:
                        if not relator_code_cran[key]["wikidata"] in self.relator_map:
                            self.relator_map[relator_code_cran[key]["wikidata"]] = relator_code_cran[key]

        if wikidata_property in self.relator_map:
            return self.relator_map[wikidata_property]
        else:
            # by default we return "P767" - contributor
            return self.relator_map["P767"]

def _index(the_list, the_value):
    try:
        return the_list.index(the_value)
    except ValueError:
        return None

def _init_count(entity):
    '''
    Init a count attribute to 1 for every source references (P248)/
    This is done recursively directly on the dictionary instance.
    '''
    if entity == None:
        return None
    elif isinstance(entity, list):
        for value in entity:
            _init_count(value)
    elif isinstance(entity, dict):
        for key, value in entity.items():
            if key == "P248":
                if not 'count' in entity["P248"]:
                    try:
                        entity["P248"]['count'] = 1
                    except:
                        pass
            else:
                _init_count(entity[key])
    return entity

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Create the knowledge base using the staging area graph and the produced deduplication/disambiguation decisions")
    parser.add_argument("--config", default="./config.yaml", help="path to the config file, default is ./config.yaml") 
    parser.add_argument("--reset", action="store_true", help="reset existing graph and reload the processed staging area graph") 

    args = parser.parse_args()
    config_path = args.config
    to_reset = args.reset

    kb = knowledgeBase(config_path=config_path)
    kb.init(config_path=config_path, reset=to_reset)

