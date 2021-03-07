'''
Actual Knowledge Base level with deduplicated/disambiguated entities coming from the staging area. 
No new entities and relations are created at this level, they are imported from the staging area and conflated. 

This database is used by the service API and appropiate index are built for this purpose.  
'''

 
import os
import sys
import json
from arango import ArangoClient
sys.path.append(os.path.abspath('./common'))
from arango_common import CommonArangoDB
sys.path.append(os.path.abspath('./merge'))
from populate_staging_area import StagingArea, _project_entity_id_collection
import argparse
from tqdm import tqdm

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

    def __init__(self, config_path="./config.json"):
        self.load_config(config_path)

        # create database if it doesn't exist
        if not self.sys_db.has_database(self.database_name):
            self.sys_db.create_database(self.database_name)

        self.db = self.client.db(self.database_name, username=self.config['arango_user'], password=self.config['arango_pwd'])

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

    def init(self, reset=False):
        if reset:
            self.reset()
            
        self.init_documents()
        self.init_organizations()
        self.init_licenses()
        self.init_persons()
        self.init_software()

        self.set_up_relations()

    def init_documents(self):
        '''
        Load documents with merging information from the staging area. Keep track of conflation for 
        updating relations. 
        '''
        stagingArea = StagingArea(config_path=config_path)

        print("\ndocument kb loading")
        total_results = stagingArea.documents.count()
        page_size = 1000
        nb_pages = (total_results // page_size)+1

        print("total documents:", total_results, ", nb. steps:", nb_pages)

        for page_rank in tqdm(range(0, nb_pages)):

            cursor = stagingArea.db.aql.execute(
                'FOR doc IN documents LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) + ' RETURN doc', ttl=3600
            )
        
            for document in cursor:
                # check if the document entry shall be merged
                if stagingArea.staging_graph.has_vertex("merging_entities/" + document['_key']):
                    # this document has to be merged with other ones
                    merging_entity_item = stagingArea.merging_entities.get("merging_entities/" + document['_key'])
                    merging_list_id = merging_entity_item['list_id']

                    # get the list content
                    merging_list_item = stagingArea.merging_lists.get(merging_list_id)
                    merging_list = merging_list_item['data']

                    # we have to check the rank of the document entity in the list (of entity _id), only the first one is canonical
                    rank = _index(merging_list, document['_id'])
                    if rank != None and rank == 0:
                        # merge
                        start = True 
                        for local_id in merging_list:
                            if start:
                                start = False
                                merged_document = stagingArea.documents.get(local_id)
                                continue
                            to_merge_document = stagingArea.documents.get(local_id)
                            merged_document = self.aggregate_with_merge(merged_document, to_merge_document)
                        self.kb_graph.insert_vertex('documents', merged_document)
                    else:
                        continue
                else:
                    # no merging involved with this document, we add it to the KB and continue
                    self.kb_graph.insert_vertex('documents', document)

        print("number of loaded documents after deduplication:", self.documents.count())


    def init_organizations(self):
        '''
        Load organizations with merging information from the staging area. Keep track of conflation for 
        updating relations.  
        '''
        stagingArea = StagingArea(config_path=config_path)

        print("\norganizations kb loading")
        total_results = stagingArea.organizations.count()
        page_size = 1000
        nb_pages = (total_results // page_size)+1

        print("total organizations:", total_results, ", nb. steps:", nb_pages)

        for page_rank in tqdm(range(0, nb_pages)):

            cursor = stagingArea.db.aql.execute(
                'FOR doc IN organizations LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) + ' RETURN doc', ttl=3600
            )

            for organization in cursor:
                # note: no merging done previously for the moment
                self.kb_graph.insert_vertex('organizations', organization)

        print("number of loaded organizations after deduplication:", self.organizations.count())


    def init_licenses(self):
        '''
        Load licenses with merging information from the staging area. Keep track of conflation for 
        updating relations. 
        '''
        stagingArea = StagingArea(config_path=config_path)

        print("\nlicenses kb loading")
        total_results = stagingArea.licenses.count()
        page_size = 1000
        nb_pages = (total_results // page_size)+1

        print("total licenses:", total_results, ", nb. steps:", nb_pages)

        for page_rank in tqdm(range(0, nb_pages)):

            cursor = stagingArea.db.aql.execute(
                'FOR doc IN licenses LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) + ' RETURN doc', ttl=3600
            )

            for license in cursor:
                # no merging done previously for the moment
                self.kb_graph.insert_vertex('licenses', license)

        print("number of loaded licenses after deduplication:", self.licenses.count())


    def init_persons(self):
        '''
        Load person entities with merging information from the staging area. Keep track of conflation for 
        updating relations. 
        '''
        stagingArea = StagingArea(config_path=config_path)

        print("\npersons kb loading")
        total_results = stagingArea.persons.count()
        page_size = 1000
        nb_pages = (total_results // page_size)+1

        print("total persons:", total_results, ", nb. steps:", nb_pages)

        for page_rank in tqdm(range(0, nb_pages)):

            cursor = stagingArea.db.aql.execute(
                'FOR doc IN persons LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) + ' RETURN doc', ttl=3600
            )

            for person in cursor:
                # check if the person entry should be merged
                if stagingArea.staging_graph.has_vertex("merging_entities/" + person['_key']):
                    # this person has to be merged with other ones
                    merging_entity_item = stagingArea.merging_entities.get("merging_entities/" + person['_key'])
                    merging_list_id = merging_entity_item['list_id']

                    # get the list content
                    merging_list_item = stagingArea.merging_lists.get(merging_list_id)
                    merging_list = merging_list_item['data']

                    # we have to check the rank of the person entity in the list (of entity _id), only the first one is canonical
                    rank = _index(merging_list, person['_id'])
                    if rank != None and rank == 0:
                        # merge
                        start = True 
                        for local_id in merging_list:
                            if start:
                                start = False
                                merged_person = stagingArea.persons.get(local_id)
                                continue
                            to_merge_person = stagingArea.persons.get(local_id)
                            merged_person = self.aggregate_with_merge(merged_person, to_merge_person)
                        self.kb_graph.insert_vertex('persons', merged_person)
                    else:
                        continue
                else:
                    # no merging involved with this person, we add it to the KB and continue
                    self.kb_graph.insert_vertex('persons', person)

        print("number of loaded persons after deduplication:", self.persons.count())


    def init_software(self):
        '''
        Load software entities with merging information from the staging area. Keep track of conflation for 
        updating relations. 
        '''
        stagingArea = StagingArea(config_path=config_path)

        print("\nsoftware kb loading")
        total_results = stagingArea.software.count()
        page_size = 1000
        nb_pages = (total_results // page_size)+1

        print("total software:", total_results, ", nb. steps:", nb_pages)

        for page_rank in tqdm(range(0, nb_pages)):

            cursor = stagingArea.db.aql.execute(
                'FOR doc IN software LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) + ' RETURN doc', ttl=3600
            )

            for software in cursor:
                # check if the software entry should be merged
                if stagingArea.staging_graph.has_vertex("merging_entities/" + software['_key']):
                    # this software has to be merged with other ones
                    merging_entity_item = stagingArea.merging_entities.get("merging_entities/" + software['_key'])
                    merging_list_id = merging_entity_item['list_id']

                    # get the list content
                    merging_list_item = stagingArea.merging_lists.get(merging_list_id)
                    merging_list = merging_list_item['data']

                    # we have to check the rank of the software entity in the list (of entity _id), only the first one is canonical
                    rank = _index(merging_list, software['_id'])
                    if rank != None and rank == 0:
                        # merge
                        start = True 
                        for local_id in merging_list:
                            if start:
                                start = False
                                merged_software = stagingArea.software.get(local_id)
                                continue
                            to_merge_software = stagingArea.software.get(local_id)
                            merged_software = self.aggregate_with_merge(merged_software, to_merge_software)
                        self.kb_graph.insert_vertex('software', merged_software)
                    else:
                        continue
                else:
                    # no merging involved with this software, we add it to the KB and continue
                    self.kb_graph.insert_vertex('software', software)

        print("number of loaded software after deduplication:", self.software.count())


    def set_up_relations(self):
        '''
        Load relations from staging area and update them based on merged vertex.
        '''
        stagingArea = StagingArea(config_path=config_path)

        print("\nactor relations kb loading")

        total_results = stagingArea.actors.count()
        page_size = 1000
        nb_pages = (total_results // page_size)+1

        print("total actor edges:", total_results, ", nb. steps:", nb_pages)

        for page_rank in tqdm(range(0, nb_pages)):

            cursor = stagingArea.db.aql.execute(
                'FOR doc IN actors LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) + ' RETURN doc', ttl=3600
            )

            for actor in cursor:
                # check "from" and "to" vertex
                from_entity_id = actor["_from"]
                to_entity_id = actor["_to"]

                # if vertex does not exist, find the list and the canonical vertex where it has been merged
                if not self.kb_graph.has_vertex(from_entity_id):
                    from_merged_entity_id = _project_entity_id_collection(from_entity_id, "merging_entities")
                    merging_entity_item = stagingArea.merging_entities.get(from_merged_entity_id)
                    if merging_entity_item != None:
                        merging_list_id = merging_entity_item['list_id']
                        merging_list_item = stagingArea.merging_lists.get(merging_list_id)
                        merging_list = merging_list_item['data']
                        new_from_entity_id = merging_list[0]
                        actor["_from"] = new_from_entity_id

                if not self.kb_graph.has_vertex(to_entity_id):
                    to_merged_entity_id = _project_entity_id_collection(to_entity_id, "merging_entities")
                    merging_entity_item = stagingArea.merging_entities.get(to_merged_entity_id)
                    if merging_entity_item != None:
                        merging_list_id = merging_entity_item['list_id']
                        merging_list_item = stagingArea.merging_lists.get(merging_list_id)
                        merging_list = merging_list_item['data']
                        new_to_entity_id = merging_list[0]
                        actor["_to"] = new_from_entity_id

                # update relation with merged vertex
                print(actor)
                self.kb_graph.insert_edge('actors', actor)

        print("number of loaded software after deduplication:", self.actors.count())


def _index(the_list, the_value):
    try:
        return the_list.index(the_value)
    except ValueError:
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Create the knowledge base using the staging area graph and the produced deduplication/disambiguation decisions")
    parser.add_argument("--config", default="./config.json", help="path to the config file, default is ./config.json") 
    parser.add_argument("--reset", action="store_true", help="reset existing graph and reload the processed staging area graph") 

    args = parser.parse_args()
    config_path = args.config
    to_reset = args.reset

    kb = knowledgeBase(config_path=config_path)
    kb.init(reset=to_reset)

