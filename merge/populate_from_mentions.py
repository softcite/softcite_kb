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

        if not stagingArea.staging_graph.has_vertex(local_doc["_id"]):
            stagingArea.staging_graph.insert_vertex("documents", local_doc)

        # there are two relations to be built at this level:
        # - authorship based on "author" metadata field (edge "actor" from "persons" to "documents")
        # - funding based on crossref "funder" metadata field (edge "funding" from "organizations" to "documents")

        

        # we process all the annotations from this document, which makes possible some (modest) optimizations

        cursor_annot = stagingArea.db.aql.execute(
          "FOR doc IN annotations FILTER doc.document.$oid == '" + local_doc['_key'] + "' RETURN doc", ttl=60
        )

        software_name_processed = {}
        index_annot = 0
        for annotation in cursor_annot:
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
                new_entity = True
            else:
                # otherwise get the existing entity for this software
                software = software_name_processed[annotation["software-name"]["normalizedForm"]]

            # version info (P348)
            if "version" in annotation and not check_value_exists(software["claims"], "P348", annotation["version"]):
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

            if new_entity:
                local_id = stagingArea.get_uid()
                software['_key'] = local_id
                software['_id'] = "software/" + local_id
                stagingArea.staging_graph.insert_vertex("software", software)
                software_name_processed[annotation["software-name"]["normalizedForm"]] = software
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
            relation["_id"] = "citations/" + relation["_key"]
            stagingArea.staging_graph.insert_edge("citations", edge=relation)

            # bibliographical reference attached to the citation context, this will be represented as 
            # a reference relation, from the citing document to the cited document, with related software information
            # in the relation
            if "references" in annotation:
                for reference in annotation["references"]:

                    # store the referenced document as document vertex (it will be deduplicated in a further stage) if not already present
                    referenced_document = None
                    cursor_ref = stagingArea.documents.find({'_key': reference["reference_id"]["$oid"]}, skip=0, limit=1)
                    if cursor_ref.count()>0:
                        referenced_document = cursor_ref.next()

                    if referenced_document == None:
                        # this is the usual case. we create a new document entity from the extracted bibliographical reference metadata
                        referenced_document = stagingArea.init_entity_from_template("document", source=source_ref)
                        if referenced_document is None:
                            raise("cannot init document entity from default template")

                        referenced_document['_key'] = reference["reference_id"]["$oid"]
                        referenced_document['_id'] = "documents/" + reference["reference_id"]["$oid"]

                        # get the metadata from the mentions database
                        mention_reference = stagingArea.db.collection('references').get({'_key': reference["reference_id"]["$oid"]})
                        if mention_reference is None:
                            print("warning: reference object indicated in an annotation does not exist, _key:", reference["reference_id"]["$oid"])
                            continue

                        # document metadata stays as they are (e.g. full CrossRef record)
                        referenced_document['metadata'] = stagingArea.tei2json(mention_reference['tei'])

                        # DOI index
                        if "DOI" in referenced_document['metadata']:
                            referenced_document["index_doi"] = referenced_document['metadata']['DOI'].lower()

                        # title/first author last name index
                        if "title" in referenced_document['metadata'] and "author" in referenced_document['metadata']:
                            local_key = stagingArea.title_author_key(referenced_document['metadata']['title'], referenced_document['metadata']['author'])
                            if local_key != None:
                                referenced_document["index_title_author"] = local_key

                        if not stagingArea.staging_graph.has_vertex(referenced_document["_id"]):
                            stagingArea.staging_graph.insert_vertex("documents", referenced_document)


                    # property is "cites work" (P2860) that we can include in the citation edge
                    local_value = {}
                    local_value["value"] = reference["reference_id"]["$oid"]
                    local_value["datatype"] = "external-id"
                    local_value["references"] = []
                    local_value["references"].append(source_ref)

                    # bounding box in qualifier
                    # relevant property is "relative position within image" (P2677) 
                    # note: currently bounding box for the context sentence not outputted by the software-mention module, but
                    # we can load it if present for the future
                    if "boundingBoxes" in reference:
                        local_qualifier = {}
                        local_qualifier_value = {}
                        local_qualifier_value["value"] = reference["boundingBoxes"]
                        local_qualifier_value["datatype"] = "string"
                        local_qualifier["P2677"] = local_qualifier_value
                        local_value["qualifiers"] = []
                        local_value["qualifiers"].append(local_qualifier)

                    # refkey in qualifier (number of the reference in the full bibliographical section of the citing paper)
                    if "refkey" in reference:
                        local_qualifier = {}
                        local_qualifier_value = {}
                        local_qualifier_value["value"] = reference["refkey"]
                        local_qualifier_value["datatype"] = "string"
                        local_qualifier["PA02"] = local_qualifier_value
                        if "qualifiers" not in local_value:
                            local_value["qualifiers"] = []
                        local_value["qualifiers"].append(local_qualifier)

                    # label is the reference marker used by the citing paper as call-out to the full reference entry 
                    if "label" in reference:
                        local_qualifier = {}
                        local_qualifier_value = {}
                        local_qualifier_value["value"] = reference["label"]
                        local_qualifier_value["datatype"] = "string"
                        local_qualifier["PA03"] = local_qualifier_value
                        if "qualifiers" not in local_value:
                            local_value["qualifiers"] = []
                        local_value["qualifiers"].append(local_qualifier)

                    if not "P2860" in relation["claims"]:
                        relation["claims"]["P2860"] = []
                    relation["claims"]["P2860"].append(local_value)

                    # reference relationwith specific edge
                    relation_ref = {}
                    relation_ref["claims"] = {}
                    # "P2860" property "cites work "
                    relation_ref["claims"]["P2860"] = []
                    local_value = {}
                    local_value["references"] = []
                    local_value["references"].append(source_ref)
                    relation_ref["claims"]["P2860"].append(local_value)

                    relation_ref["_from"] = local_doc['_id']
                    relation_ref["_to"] = referenced_document['_id']

                    relation_ref["_key"] = local_doc["_key"] + "_" + referenced_document['_key'] + "_" + str(index_annot)
                    relation_ref["_id"] = "references/" + relation_ref["_key"]
                    if not stagingArea.staging_graph.has_edge(relation_ref["_id"]):
                        stagingArea.staging_graph.insert_edge("references", edge=relation_ref)

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

