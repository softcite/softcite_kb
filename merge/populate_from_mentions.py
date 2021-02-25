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
      'FOR doc IN documents RETURN doc', ttl=3600
    )

    for document in cursor:
        # document as document vertex collection
        local_doc = stagingArea.init_entity_from_template("document", source=source_ref)
        if local_doc is None:
            raise("cannot init document entity from default template")

        local_doc['_key'] = document["_key"]
        local_doc['_id'] = "documents/" + document["_key"]

        # document metadata stays as they are (e.g. full CrossRef record)
        local_doc['metadata'] = document['metadata']

        if not self.staging_graph.has_vertex(local_doc["_id"]):
            self.staging_graph.insert_vertex("documents", local_doc)

        # there are two relations to be built at this level:
        # - authorship based on "author" metadata field (edge "actor" to "person")
        # - funding based on "funder" metadata field (edge )

        


    cursor = stagingArea.db.aql.execute(
      'FOR doc IN annotations RETURN doc', ttl=1000
    )

    for annotation in cursor:
        # annotations from the same document lead to a new software entity (to be further disambiguated)



        software = stagingArea.init_entity_from_template("software", source=source_ref)
        if software is None:
            raise("cannot init software entity from default template")

        software['labels'] = annotation["software-name"]["normalizedForm"]
        # add the normalized form as property value too, with associated bounding boxes

        
        # version info (P348)
        if "version" in annotation:
            local_value = {}
            local_value["value"] = annotation["Version"]
            local_value["datatype"] = "string"
            local_value["references"] = []
            local_value["references"].append(source_ref)
            software["claims"]["P348"] = []
            software["claims"]["P348"].append(local_value)

            # associated bounding boxes


        if "publisher" in annotation:
            # publisher (P123) 
            local_value = {}
            local_value["value"] = annotation["publisher"]
            local_value["datatype"] = "string"
            local_value["references"] = []
            local_value["references"].append(source_ref)
            software["claims"]["P123"] = []
            software["claims"]["P123"].append(local_value)

            # associated bounding boxes


        if "url" in annotation:
            # reference URL (P854) 
            local_value = {}
            local_value["value"] = annotation["url"]
            local_value["datatype"] = "url"
            local_value["references"] = []
            local_value["references"].append(source_ref)
            software["claims"]["P854"] = []
            software["claims"]["P854"].append(local_value)

            # associated bounding boxes


        if "context" in annotation:    
            # quotation or excerpt (P7081) 
            local_value = {}
            local_value["value"] = annotation["context"]
            local_value["datatype"] = "string"
            local_value["references"] = []
            local_value["references"].append(source_ref)
            software["claims"]["P7081"] = []
            software["claims"]["P7081"].append(local_value)

            # associated bounding boxes
            # note: currently not outputted by the software-mention module !


        #if "wikipediaExternalRef" in annotation:



        # the predicted wikidata entity for the software is represented with property "said to be the same" (P460)
        # which is defnied as "said to be the same as that item, but it's uncertain or disputed"
        if "wikidataId" in annotation:
            local_value = {}
            local_value["value"] = annotation["wikidataId"]
            local_value["datatype"] = "wikibase-item"
            local_value["references"] = []
            local_value["references"].append(source_ref)
            software["claims"]["P460"] = []
            software["claims"]["P460"].append(local_value)




        # relations to be built at this level:
        # - citations based on software mention in a document, which will include context sentence, coordinates, etc.
        #   here document are fully specified (with PDF hash, page coordinates, etc.) because it has been "text-mined"
        # - references, which relate a software or a document (where the reference is expressed) to a document 
        #   (and less frequently to a software), the document here can be simply a set of bibliographical metadata or
        #   a fully specified document

