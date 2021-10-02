'''
Populate the staging area graph from the software mention imported documents
'''

import os
import json
from arango import ArangoClient
from populate_staging_area import StagingArea
import logging
import logging.handlers
from tqdm import tqdm

def populate(stagingArea):

    database_name_mentions = "mentions"

    print("Populate staging area from software mention import")
    if not stagingArea.sys_db.has_database(database_name_mentions):
        logging.error("Software mention import database does not exist: you need to first import the software mention resources")

    stagingArea.db = stagingArea.client.db(database_name_mentions, username=stagingArea.config['arangodb']['arango_user'], password=stagingArea.config['arangodb']['arango_pwd'])

    populate_mentions(stagingArea, stagingArea.get_source(database_name_mentions))

def populate_mentions(stagingArea, source_ref):
    '''
    Software mentions at this stage are all represented as independent software entity (very light-weight and with 
    the few extracted attributes). The information related to the mention in context are represented with the edge 
    relation "citations", with a "quotes work" (P6166) property to store the software (=work) mentioned and "quotation" 
    (P7081) for storing the whole context of mention (the target sentence). 
    Other relations built are funding (via Crossref funders) and references. 
    '''

    # given the possible number of documents, we use pagination rather than a large ttl 

    cursor = stagingArea.db.aql.execute(
      'FOR doc IN documents RETURN doc', full_count=True
    )

    stats = cursor.statistics()
    total_results = 0
    if 'fullCount' in stats:
        total_results = stats['fullCount']

    page_size = 1000
    nb_pages = (total_results // page_size)+1

    print("entries:", total_results, ", nb. steps:", nb_pages)

    for page_rank in tqdm(range(0, nb_pages)):

        cursor = stagingArea.db.aql.execute(
            'FOR doc IN documents LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) + ' RETURN doc', ttl=3600
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

            if "DOI" in document['metadata']:
                local_doc['index_doi'] = document['metadata']['DOI'].lower()
            # unfortunately the casing of the key DOI field is unreliable
            if "doi" in document['metadata']:
                local_doc['index_doi'] = document['metadata']['doi'].lower()

            if "title" in document['metadata'] and len(document['metadata']['title'])>0 and 'author' in document['metadata'] and len(document['metadata']['author'])>0:
                local_title = document['metadata']['title']
                local_author = None
                if 'author' in document['metadata']:
                    # we normally always have an author field
                    local_author = document['metadata']['author']

                if local_author != None and local_title != None:
                    local_title_author_key = stagingArea.title_author_key(local_title, local_author)
                    if local_title_author_key != None and len(local_title_author_key)>0:
                        local_doc['index_title_author'] = local_title_author_key

            if not stagingArea.staging_graph.has_vertex(local_doc["_id"]):
                stagingArea.staging_graph.insert_vertex("documents", local_doc)

            # there are two relations to be built at this level:
            # - authorship based on "author" metadata field (edge "actor" from "persons" to "documents")

            # -> as we consider here text-mined documents, we might better not important every authors as entities at this stage
            # and keep only authors from key references cited together with software in mention

            # - funding based on crossref "funder" metadata field (edge "funding" from "organizations" to "documents")        
            '''
            if 'funder' in document['metadata'] and len(document['metadata']['funder'])>0:
                for funder in document['metadata']['funder']:
                    # in WorkFunder, funder is defined by 'name', a 'DOI' (uppercase here, related to the funder), 
                    # 'country' (conversion from medline/pubmed) 
                    # funding is defined by 'award' [array] (optional)

                    # the DOI here contains thefunder id and it should make possible to get a full CrossRef funder 
                    # entry /funders/{id}

                    # DOI 10.13039/100004440, funder id is 100004440
                    # https://api.crossref.org/funders/100004440/ -> Wellcome

                    # apparently 10.13039/ is the prefix for all funders? 

                    funderID = None
                    if "DOI" in funder:
                        funderDOI = funder['DOI']
                        ind = funderDOI.find('/')
                        if ind != -1:
                            funderID = funderDOI[ind+1:]

                    if funderID == None:
                        continue

                    # full funder record at Crossref

                    # Crossref funder ID is P3153
                    # create an organization entity, if not already present with this funder identifier via P3153
                                    

                    replaced = False
                    # we check if the organization is not already in the KB, and aggregate/merge with this existing one if yes
                    cursor = stagingArea.db.aql.execute(
                        'FOR doc IN organizations FILTER ['+funderID+'] ANY IN doc["claims"]["P3153"][*]["value"] LIMIT 1 RETURN doc'
                    )

                    if cursor.count()>0:
                        existing_organization = cursor.next()
                        existing_organization = stagingArea.aggregate_with_merge(existing_organization, organization)
                        #del existing_software["_rev"]
                        #print(existing_software)
                        stagingArea.staging_graph.update_vertex(existing_organization)
                        organization = existing_organization
                        replaced = True

                    if not replaced:


                        # organization as document vertex collection
                        local_org = stagingArea.init_entity_from_template("organization", source=source_ref)
                        if local_org is None:
                            raise("cannot init organization entity from default template") 


                        organization["labels"] = org_name
                        local_org_id = stagingArea.get_uid()
                        organization["_key"] = local_org_id
                        organization["_id"] = "organizations/" + organization["_key"]
                        stagingArea.staging_graph.insert_vertex("organizations", organization)

                    # funding relation
                    relation = {}
                    relation["claims"] = {}
                    relation["claims"]['P8324'] = [ {"references": [ source_ref ] } ]
                    relation["_from"] = organization["_id"]
                    relation["_to"] = "documents/" + document["_key"]
                    relation["_id"] = "funding/" + organization["_key"] + "_" + document["_key"]
                    stagingArea.staging_graph.insert_edge("funding", edge=relation)
            '''

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
                    software["index_entity"] = annotation["wikidataId"]
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

                # store original software name string - always present normally
                # we use property P6166 ("quote work", here the work is the mentioned software)
                if "software-name" in annotation:
                    local_value = {}
                    local_value["value"] = annotation["software-name"]["normalizedForm"]
                    local_value["datatype"] = "string"
                    local_value["references"] = []
                    local_value["references"].append(source_ref)
                    
                    # bounding box in qualifier
                    # relevant property is "relative position within image" (P2677) 
                    if "boundingBoxes" in annotation["software-name"]:
                        local_qualifier = {}
                        local_qualifier_value = {}
                        local_qualifier_value["value"] = annotation["software-name"]["boundingBoxes"]
                        local_qualifier_value["datatype"] = "string"
                        local_qualifier["P2677"] = local_qualifier_value
                        local_value["qualifiers"] = []
                        local_value["qualifiers"].append(local_qualifier)

                    relation["claims"]["P6166"] = []
                    relation["claims"]["P6166"].append(local_value)

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
                                logging.warning("warning: reference object indicated in an annotation does not exist, _key: " + reference["reference_id"]["$oid"])
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

                         # reference relation with specific edge
                        relation_ref = {}

                        relation_ref["claims"] = {}
                        # "P2860" property "cites work ", add software associated to the citation context,
                        relation_ref["claims"]["P2860"] = []
                        local_value = {}
                        local_value["value"] = "software/" + software['_key']
                        local_value["datatype"] = "external-id"
                        local_value["references"] = []
                        local_value["references"].append(source_ref)
                        relation_ref["claims"]["P2860"].append(local_value)

                        # we add an index to the software identifier, which will be useful when filtering the
                        # references related to a given software
                        relation_ref["index_software"] = "software/" + software['_key']

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

