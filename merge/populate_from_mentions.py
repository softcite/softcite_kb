'''
Populate the staging area graph from the software mention imported documents
'''

import os
import json
from arango import ArangoClient
from populate_staging_area import StagingArea


def populate(stagingArea):

    database_name_mentions = "mentions"

    print("Populate staging area from software mention import")
    if not stagingArea.sys_db.has_database(database_name_mentions):
        print("Software mention import database does not exist: you need to first import the software mention resources")

    stagingArea.db = stagingArea.client.db(database_name_mentions, username=stagingArea.config['arango_user'], password=stagingArea.config['arango_pwd'])

    populate_mentions(stagingArea, stagingArea.get_source(database_name_mentions))

def populate_wikidata(stagingArea, source_ref):
    '''
    Software mentions at this stage are all represented as independent software entity (very light weight and with 
    the few extracted attributes). The information related to the mention in context are represented with the edge 
    relation "citations", with a "quotes work" (P6166) property to store the context. 
    Other relations built are authorship, funding and references. 
    '''
    cursor = stagingArea.db.aql.execute(
      'FOR doc IN documents RETURN doc', ttl=1000
    )

    for document in cursor:
        # document as document vertex collection

        # there are two relations to be built at this level:
        # - authorship based on "author" metadata field (edge "actor" to "person")
        # - funding based on "funder" metadata field (edge )

        


    cursor = stagingArea.db.aql.execute(
      'FOR doc IN annotations RETURN doc', ttl=1000
    )

    for annotation in cursor:
        # annotations from the same document lead to a new software entity (to be further disambiguated)

        # relations to be built at this level:
        # - citations based on software mention in a document, which will include context sentence, coordinates, etc.
        #   here document are fully specified (with PDF hash, page coordinates, etc.) because it has been "text-mined"
        # - references, which relate a software or a document (where the reference is expressed) to a document 
        #   (and less frequently to a software), the document here can be simply a set of bibliographical metadata or
        #   a fully specified document

