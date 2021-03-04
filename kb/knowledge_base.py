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
            self.staging_graph = self.db.graph(self.graph_name)
        else:
            self.staging_graph = self.db.create_graph(self.graph_name)

        # init vertex collections if they don't exist
        if not self.staging_graph.has_vertex_collection('software'):
            self.software = self.staging_graph.create_vertex_collection('software')
        else:
            self.software = self.staging_graph.vertex_collection('software')

        if not self.staging_graph.has_vertex_collection('persons'):
            self.persons = self.staging_graph.create_vertex_collection('persons')
            # we add a hash index on the orcid identifier
            self.index_orcid = self.persons.add_hash_index(fields=['index_orcid'], unique=True, sparse=True)
        else:
            self.persons = self.staging_graph.vertex_collection('persons')

        if not self.staging_graph.has_vertex_collection('organizations'):
            self.organizations = self.staging_graph.create_vertex_collection('organizations')
        else:
            self.organizations = self.staging_graph.vertex_collection('organizations')

        if not self.staging_graph.has_vertex_collection('documents'):
            self.documents = self.staging_graph.create_vertex_collection('documents')
        else:
            self.documents = self.staging_graph.vertex_collection('documents')

        if not self.staging_graph.has_vertex_collection('licenses'):
            self.licenses = self.staging_graph.create_vertex_collection('licenses')
        else:
            self.licenses = self.staging_graph.vertex_collection('licenses')

        # init edge collections if they don't exist
        if not self.staging_graph.has_edge_collection('citations'):
            self.citations = self.staging_graph.create_edge_definition(
                edge_collection='citations',
                from_vertex_collections=['documents'],
                to_vertex_collections=['software']
            )
        else:
            self.citations = self.staging_graph.edge_collection('citations')

        if not self.staging_graph.has_edge_collection('references'):
            self.references = self.staging_graph.create_edge_definition(
                edge_collection='references',
                from_vertex_collections=['software', 'documents'],
                to_vertex_collections=['software', 'documents']
            )
        else:
            self.references = self.staging_graph.edge_collection('references')

        if not self.staging_graph.has_edge_collection('actors'):
            self.actors = self.staging_graph.create_edge_definition(
                edge_collection='actors',
                from_vertex_collections=['persons'],
                to_vertex_collections=['software', 'documents']
            )
        else:
            self.actors = self.staging_graph.edge_collection('actors')

        if not self.staging_graph.has_edge_collection('copyrights'):
            self.copyrights = self.staging_graph.create_edge_definition(
                edge_collection='copyrights',
                from_vertex_collections=['persons', 'organizations'],
                to_vertex_collections=['software']
            )
        else:
            self.copyrights = self.staging_graph.edge_collection('copyrights')

        if not self.staging_graph.has_edge_collection('dependencies'):
            self.dependencies = self.staging_graph.create_edge_definition(
                edge_collection='dependencies',
                from_vertex_collections=['software'],
                to_vertex_collections=['software']
            )
        else:
            self.dependencies = self.staging_graph.edge_collection('dependencies')

        if not self.staging_graph.has_edge_collection('funding'):
            self.funding = self.staging_graph.create_edge_definition(
                edge_collection='funding',
                from_vertex_collections=['software', "documents"],
                to_vertex_collections=['organizations']
            )
        else:
            self.funding = self.staging_graph.edge_collection('funding')


    def reset(self):
        # edge collections
        if self.staging_graph.has_edge_collection('citations'):
            self.staging_graph.delete_edge_definition('citations', purge=True)

        if self.staging_graph.has_edge_collection('references'):
            self.staging_graph.delete_edge_definition('references', purge=True)

        if self.staging_graph.has_edge_collection('actors'):
            self.staging_graph.delete_edge_definition('actors', purge=True)

        if self.staging_graph.has_edge_collection('copyrights'):
            self.staging_graph.delete_edge_definition('copyrights', purge=True)

        if self.staging_graph.has_edge_collection('dependencies'):
            self.staging_graph.delete_edge_definition('dependencies', purge=True)

        if self.staging_graph.has_edge_collection('funding'):
            self.staging_graph.delete_edge_definition('funding', purge=True)

        # vertex collections
        if self.staging_graph.has_vertex_collection('software'):
            self.staging_graph.delete_vertex_collection('software', purge=True)

        if self.staging_graph.has_vertex_collection('persons'):
            self.staging_graph.delete_vertex_collection('persons', purge=True)

        if self.staging_graph.has_vertex_collection('organizations'):
            self.staging_graph.delete_vertex_collection('organizations', purge=True)

        if self.staging_graph.has_vertex_collection('documents'):
            self.staging_graph.delete_vertex_collection('documents', purge=True)

        if self.staging_graph.has_vertex_collection('licenses'):
            self.staging_graph.delete_vertex_collection('licenses', purge=True)

        self.software = self.staging_graph.create_vertex_collection('software')
        self.persons = self.staging_graph.create_vertex_collection('persons')
        self.index_orcid = self.persons.add_hash_index(fields=['index_orcid'], unique=True, sparse=True)
        self.organizations = self.staging_graph.create_vertex_collection('organizations')
        self.documents = self.staging_graph.create_vertex_collection('documents')
        self.licenses = self.staging_graph.create_vertex_collection('licenses')

        self.citations = self.staging_graph.create_edge_definition(
                edge_collection='citations',
                from_vertex_collections=['documents'],
                to_vertex_collections=['software']
            )

        self.references = self.staging_graph.create_edge_definition(
                edge_collection='references',
                from_vertex_collections=['software', 'documents'],
                to_vertex_collections=['software', 'documents']
            )

        self.actors = self.staging_graph.create_edge_definition(
                edge_collection='actors',
                from_vertex_collections=['persons'],
                to_vertex_collections=['software', 'documents']
            )

        self.copyrights = self.staging_graph.create_edge_definition(
                edge_collection='copyrights',
                from_vertex_collections=['persons', 'organizations'],
                to_vertex_collections=['software']
            )

        self.dependencies = self.staging_graph.create_edge_definition(
                edge_collection='dependencies',
                from_vertex_collections=['software'],
                to_vertex_collections=['software']
            )

        self.funding = self.staging_graph.create_edge_definition(
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

        cursor = stagingArea.db.aql.execute(
            'FOR doc IN documents RETURN doc', ttl=3600
        )
        # note: given the possible number of documents, we should rather use pagination than a large ttl 
        for document in cursor:
            # check if the document entry shall be merged
            if stagingArea.staging_graph.has_vertex("merging_entities/" + document['_key']):
                # this document has to be merged with other ones
                merging_entity_item = stagingArea.staging_graph.get("merging_entities/" + document['_key'])
                merging_list_ids = merging_entity_item['list_id']

                # we have to check the rank of the document entity in the list (of entity _id), only the first one is canonical
                rank = _index(merging_list_ids, document['_id'])
                if rank != None and rank == 0:
                    # merge
                    start = True 
                    for local_id in merging_list_ids:
                        if start:
                            start = False
                            merged_document = stagingArea.staging_graph.get(local_id)
                            continue
                        to_merge_document = stagingArea.staging_graph.get(local_id)
                        merged_document = self.aggregate_with_merge(merged_document, to_merge_document)
                    self.kb_graph.insert('documents', merged_document)
                else:
                    continue
            else:
                # no merging involved with this document, we add it to the KB and continue
                self.kb_graph.insert('documents', document)

    def init_organizations(self):
        '''
        Load organizations with merging information from the staging area. Keep track of conflation for 
        updating relations.  
        '''

    def init_licenses(self):
        '''
        Load licenses with merging information from the staging area. Keep track of conflation for 
        updating relations. 
        '''
        stagingArea = StagingArea(config_path=config_path)

        cursor = stagingArea.db.aql.execute(
            'FOR doc IN licenses RETURN doc', ttl=1000
        )
        for license in cursor:
            # no merging done previously for the moment
            self.kb_graph.insert('licenses', license)

    def init_persons(self):
        '''
        Load person entities with merging information from the staging area. Keep track of conflation for 
        updating relations. 
        '''
        stagingArea = StagingArea(config_path=config_path)

        cursor = stagingArea.db.aql.execute(
            'FOR doc IN persons RETURN doc', ttl=3600
        )
        # note: given the possible number of persons, we should rather use pagination than a large ttl 
        for person in cursor:
            # check if the person entry shall be merged
            if stagingArea.staging_graph.has_vertex("merging_entities/" + person['_key']):
                # this person has to be merged with other ones
                merging_entity_item = stagingArea.staging_graph.get("merging_entities/" + person['_key'])
                merging_list_ids = merging_entity_item['list_id']

                # we have to check the rank of the person entity in the list (of entity _id), only the first one is canonical
                rank = _index(merging_list_ids, document['_id'])
                if rank != None and rank == 0:
                    # merge
                    start = True 
                    for local_id in merging_list_ids:
                        if start:
                            start = False
                            merged_person = stagingArea.staging_graph.get(local_id)
                            continue
                        to_merge_person = stagingArea.staging_graph.get(local_id)
                        merged_person = self.aggregate_with_merge(merged_person, to_merge_person)
                    self.kb_graph.insert('persons', merged_person)
                else:
                    continue
            else:
                # no merging involved with this person, we add it to the KB and continue
                self.kb_graph.insert('persons', person)



    def init_software(self):
        '''
        Load software entities with merging information from the staging area. Keep track of conflation for 
        updating relations. 
        '''


    def set_up_relations(self):
        '''
        Load relations from staging area and update them based on merged vertex.
        '''

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

