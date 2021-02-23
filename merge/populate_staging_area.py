'''
This script is creating the staging area to be populated by the documents imported from different sources, 
merging in practice heterogeneous schemas into a single one based on Wikidata. Entities and relations
are conflated only based on strong identifiers matching (e.g. orcid for persons, DOI for documents,
GitHub repo for software). Further non-trivial disambiguation and deduplication are done by the disambiguation
process creating the actual Knowledge Base.

The following collections of entities are created:
- software (covering software, packages/libraries, web applications)
- person
- organization
- document
- license

A graph structure is built on top of these vertex collections, with the following collection edges:
- citation (e.g. mention): as extracted from scientific literature, with a citation context (text and/or bounding 
  boxes)
- reference: a bibliographical reference which establishes a relation between entities (documents, software, ...)
- actor: for any human relationship (authorship, contributor, creator, maintainer, etc.), excluding intellectual 
  property relations
- copyrights: for any explicit copyright relationship between a creative work, creators and organization and a license
- dependencies: software dependencies

The staging area graph is then populated with method specific from the sources of imported documents, projecting 
the relevant information into the common graph, with additional data transformation if necessary:

> python3 merge/populate.py --config my_config.json

'''

import os
import sys
import json
from arango import ArangoClient
sys.path.append(os.path.abspath('./common'))
from arango_common import CommonArangoDB

class StagingArea(CommonArangoDB):

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

    database_name = "staging"
    graph_name = "staging_graph"

    def __init__(self, config_path="./config.json"):
        self.load_config(config_path)

        # create database if it doesn't exist
        if not self.sys_db.has_database(self.database_name):
            self.sys_db.create_database(self.database_name)

        self.db = self.client.db(self.database_name, username=self.config['arango_user'], password=self.config['arango_pwd'])

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
            self.index_orcid = self.persons.add_hash_index(fields=['index_orcid'], unique=True)
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
        self.index_orcid = self.persons.add_hash_index(fields=['index_orcid'], unique=True)
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

    def init_entity_from_template(self, template="software", source=None):
        '''
        Init an entity based on a template json present under resources/
        '''
        json_template = None
        template_file = os.path.join("data", "resources", template+"_template.json")
        if not os.path.isfile(template_file): 
            print("Error: template file does not exist for entity:", template)
            return None

        with open(template_file) as template_f:
            json_template_string = template_f.read()
            if not source is None:
                json_template_string = json_template_string.replace('[]', '[' + json.dumps(source) + ']')

            json_template = json.loads(json_template_string)

        return json_template
