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

def populate_mentions(stagingArea, source_ref):
    '''
    Software mentions at this stage are all represented as independent software entity (very light weight and with 
    the few extracted attributes). The information related to the mention in context are represented with the edge 
    relation "citations", with a "quotes work" (P6166) property to store the context. 
    Other relations built are authorship, funding and references. 
    '''
    cursor = stagingArea.db.aql.execute(
      'FOR doc IN documents RETURN doc', ttl=3600
    )

    # note: given the possible number of documents, we should rather use pagination than a large ttl 

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

        


        # we process all the annotations from this document, which makes possible some (modest) optimizations

        cursor = stagingArea.db.aql.execute(
          "FOR doc IN annotations FILTER doc['document.$oid'] == " + local_doc['_id'] + "RETURN doc", ttl=60
        )

        software_name_processed = {}
        index_annot = 0
        for annotation in cursor:
            # annotations from the same document lead to a set of new software entity (to be further disambiguated)
            # software with the same name in the same document are considered as the same entity and what is 
            # extracted for each annotation is aggregated in this single entity

            new_entity = False
            if not annotation["software-name"]["normalizedForm"] in software_name_processed:
                # new entity
                software = stagingArea.init_entity_from_template("software", source=source_ref)
                if software is None:
                    raise("cannot init software entity from default template")

                software['labels'] = annotation["software-name"]["normalizedForm"]
            
                software_name_processed[annotation["software-name"]["normalizedForm"]] = software
                new_entity = True
            else:
                # otherwise get the existing entity for this software
                software = software_name_processed[annotation["software-name"]["normalizedForm"]]

            # version info (P348)
            if "version" in annotation and not check_value_exists(software["claims"], "P348", annotation["Version"]):
                local_value = {}
                local_value["value"] = annotation["version"]["normalizedForm"]
                local_value["datatype"] = "string"
                local_value["references"] = []
                local_value["references"].append(source_ref)
                if not "P348" in software["claims"]:
                    software["claims"]["P348"] = []
                software["claims"]["P348"].append(local_value)
                changed = True

            if "publisher" in annotation and not check_value_exists(software["claims"], "P123", annotation["publisher"]):
                # publisher (P123) 
                local_value = {}
                local_value["value"] = annotation["publisher"]["normalizedForm"]
                local_value["datatype"] = "string"
                local_value["references"] = []
                local_value["references"].append(source_ref)
                if not "P123" in software["claims"]:
                    software["claims"]["P123"] = []
                software["claims"]["P123"].append(local_value)
                changed = True

            if "url" in annotation and not check_value_exists(software["claims"], "P854", annotation["url"]):
                # reference URL (P854) 
                local_value = {}
                local_value["value"] = annotation["url"]["normalizedForm"]
                local_value["datatype"] = "url"
                local_value["references"] = []
                local_value["references"].append(source_ref)
                if not "P854" in software["claims"]:
                    software["claims"]["P854"] = []
                software["claims"]["P854"].append(local_value)
                changed = True

            # the predicted wikidata entity and Wikipedia english page for the software are represented with property 
            # "said to be the same" (P460), which is defined as "said to be the same as that item, but it's uncertain or disputed"
            if "wikipediaExternalRef" in annotation and not check_value_exists(software["claims"], "P460", annotation["wikipediaExternalRef"]):
                # imported from Wikimedia project (P143) 
                local_value = {}
                local_value["value"] = annotation["wikipediaExternalRef"]
                local_value["datatype"] = "url"
                local_value["references"] = []
                local_value["references"].append(source_ref)
                if not "P460" in software["claims"]:
                    software["claims"]["P460"] = []
                software["claims"]["P460"].append(local_value)
                changed = True
            
            if "wikidataId" in annotation and not check_value_exists(software["claims"], "P460", annotation["wikidataId"]):
                local_value = {}
                local_value["value"] = annotation["wikidataId"]
                local_value["datatype"] = "wikibase-item"
                local_value["references"] = []
                local_value["references"].append(source_ref)
                if not "P460" in software["claims"]:
                    software["claims"]["P460"] = []
                software["claims"]["P460"].append(local_value)
                changed = True

            # bibliographical references associated to the software could be aggregated here, possibly with count information
            # -> to be reviewed

            local_id = stagingArea.get_uid()
            software['_key'] = local_id
            software['_id'] = "software/" + local_id

            if new_entity:
                stagingArea.staging_graph.insert_vertex("software", software)
            elif changed:
                stagingArea.staging_graph.update_vertex(software)

            # relations to be built at this level:
            # - citations based on software mention in a document, which will include context sentence, coordinates, etc.
            #   here document are fully specified (with PDF hash, page coordinates, etc.) because it has been "text-mined"
            # - references, which relate a software or a document (where the reference is expressed) to a document 
            #   (and less frequently to a software), the document here can be simply a set of bibliographical metadata or
            #   a fully specified document

            relation = stagingArea.init_entity_from_template("citation", source=source_ref)
            if relation is None:
                raise("cannot init citation relation from default template")

            # store all original attributes in this citation relation, as they are in this annotation
            # version info (P348)
            if "version" in annotation:
                local_value = {}
                local_value["value"] = annotation["version"]["normalizedForm"]
                local_value["datatype"] = "string"
                local_value["references"] = []
                local_value["references"].append(source_ref)
                
                # bounding box in qualifier
                # relevant property is "relative position within image" (P2677) 
                if "boundingBoxes" in annotation["version"]:
                    local_qualifier = {}
                    local_qualifier_value = {}
                    local_qualifier_value["value"] = annotation["version"]["boundingBoxes"]
                    local_qualifier_value["datatype"] = "string"
                    local_qualifier["P2677"] = local_qualifier_value
                    local_value["qualifiers"] = []
                    local_value["qualifiers"].append(local_qualifier)

                relation["claims"]["P348"] = []
                relation["claims"]["P348"].append(local_value)

            if "publisher" in annotation:
                # publisher (P123) 
                local_value = {}
                local_value["value"] = annotation["publisher"]["normalizedForm"]
                local_value["datatype"] = "string"
                local_value["references"] = []
                local_value["references"].append(source_ref)

                # bounding box in qualifier
                # relevant property is "relative position within image" (P2677) 
                if "boundingBoxes" in annotation["publisher"]:
                    local_qualifier = {}
                    local_qualifier_value = {}
                    local_qualifier_value["value"] = annotation["publisher"]["boundingBoxes"]
                    local_qualifier_value["datatype"] = "string"
                    local_qualifier["P2677"] = local_qualifier_value
                    local_value["qualifiers"] = []
                    local_value["qualifiers"].append(local_qualifier)

                relation["claims"]["P123"] = []
                relation["claims"]["P123"].append(local_value)

            if "url" in annotation:
                # reference URL (P854) 
                local_value = {}
                local_value["value"] = annotation["url"]["normalizedForm"]
                local_value["datatype"] = "url"
                local_value["references"] = []
                local_value["references"].append(source_ref)

                # bounding box in qualifier
                # relevant property is "relative position within image" (P2677) 
                if "boundingBoxes" in annotation["url"]:
                    local_qualifier = {}
                    local_qualifier_value = {}
                    local_qualifier_value["value"] = annotation["url"]["boundingBoxes"]
                    local_qualifier_value["datatype"] = "string"
                    local_qualifier["P2677"] = local_qualifier_value
                    local_value["qualifiers"] = []
                    local_value["qualifiers"].append(local_qualifier)

                relation["claims"]["P854"] = []
                relation["claims"]["P854"].append(local_value)

            if "wikipediaExternalRef" in annotation:
                # imported from Wikimedia project (P143) 
                local_value = {}
                local_value["value"] = annotation["wikipediaExternalRef"]
                local_value["datatype"] = "url"
                local_value["references"] = []
                local_value["references"].append(source_ref)
                relation["claims"]["P460"] = []
                relation["claims"]["P460"].append(local_value)
            
            if "wikidataId" in annotation:
                local_value = {}
                local_value["value"] = annotation["wikidataId"]
                local_value["datatype"] = "wikibase-item"
                local_value["references"] = []
                local_value["references"].append(source_ref)
                relation["claims"]["P460"] = []
                relation["claims"]["P460"].append(local_value)

            if "context" in annotation:    
                # quotation or excerpt (P7081) 
                local_value = {}
                local_value["value"] = annotation["context"]
                local_value["datatype"] = "string"
                local_value["references"] = []
                local_value["references"].append(source_ref)

                # bounding box in qualifier
                # relevant property is "relative position within image" (P2677) 
                # note: currently bounding box for the context sentence not outputted by the software-mention module, but
                # we can load it if present for the future
                if "boundingBoxes" in annotation:
                    local_qualifier = {}
                    local_qualifier_value = {}
                    local_qualifier_value["value"] = annotation["boundingBoxes"]
                    local_qualifier_value["datatype"] = "string"
                    local_qualifier["P2677"] = local_qualifier_value
                    local_value["qualifiers"] = []
                    local_value["qualifiers"].append(local_qualifier)

                relation["claims"]["P7081"] = []
                relation["claims"]["P7081"].append(local_value)

            relation["_from"] = "documents/" + local_doc["_key"]
            relation["_to"] = "software/" + software['_key']
            relation["_key"] = local_doc["_key"] + "_" + software['_key'] + "_" + str(index_annot)
            stagingArea.staging_graph.insert_edge(stagingArea.citation, edge=relation)

            # bibliographical reference attached to the citation context, this will be represented as 
            # a reference relation, from the citing document to the cited document, with related software information
            # in the relation
            if "references" in annotation:
                for reference in annotation["references"]:
                     # property is "cites work" (P2860) 
                    local_value = {}
                    local_value["value"] = reference["reference_id"]["$oid"]
                    local_value["datatype"] = "external-id"
                    local_value["references"] = []
                    local_value["references"].append(source_ref)

                    # bounding box in qualifier
                    # relevant property is "relative position within image" (P2677) 
                    # note: currently bounding box for the context sentence not outputted by the software-mention module, but
                    # we can load it if present for the future
                    if "boundingBoxes" in annotation:
                        local_qualifier = {}
                        local_qualifier_value = {}
                        local_qualifier_value["value"] = annotation["boundingBoxes"]
                        local_qualifier_value["datatype"] = "string"
                        local_qualifier["P2677"] = local_qualifier_value
                        local_value["qualifiers"] = []
                        local_value["qualifiers"].append(local_qualifier)

                    if not "P2860" in relation["claims"]:
                        relation["claims"]["P2860"] = []
                    relation["claims"]["P2860"].append(local_value)

                # update citation edge document with the added reference information
                stagingArea.staging_graph.update_edge(relation)


            index_annot += 1




def check_value_exists(claim, property_name, value):
    '''
    Check in the claim if a property is present and if the property has the given value
    '''
    if property_name in claim:
        for claim_value in claim[property_name]:
            if claim_value["value"] == value:
                return True
    return False

