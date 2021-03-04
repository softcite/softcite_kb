import os
import sys
import argparse
from populate_staging_area import StagingArea


def merge(stagingArea, reset=False):

    cursor = stagingArea.db.aql.execute(
        'FOR doc IN documents RETURN doc', ttl=3600
    )

    # note: given the possible number of documents, we should rather use pagination than a large ttl 
    for document in cursor:
        # biblio-glutton matching has already been performed, so there is no particular additional 
        # metadata enrichment to be done for document
        
        merging = False

        # check DOI matching
        if 'metadata' in document:
            if 'DOI' in document['metadata'] and len(document['metadata']['DOI'])>0:
                print(document['metadata']['DOI'].lower())
                for document_match in stagingArea.documents.find({'index_doi': document['metadata']['DOI'].lower() }, skip=0):

                    if document_match['_key'] == document['_key']:
                        continue

                    '''
                    match_cursor = stagingArea.db.aql.execute(
                        "FOR doc IN annotations FILTER doc.document.$oid == '" + local_doc['_key'] + "' RETURN doc", ttl=60
                    )
                    '''

                    # update/store merging decision list 
                    print("register....")
                    stagingArea.register_merging(document_match, document)
                    merging = True

        # check title+first_author_last_name matching
        if not merging:
            if 'title' in document['metadata'] and 'author' in document['metadata']:
                local_key = stagingArea.title_author_key(document['metadata']['title'], document['metadata']['author'])
                if local_key != None:
                    for document_match in stagingArea.documents.find({'index_title_author': local_key }, skip=0):

                        if document_match['_key'] == document['_key']:
                            continue

                        # update/store merging decision list 
                        stagingArea.register_merging(document_match, document)
                        merging = True


    cursor = stagingArea.db.aql.execute(
        'FOR doc IN organizations RETURN doc', ttl=3600
    )

    # note: given the possible number of documents, we should rather use pagination than a large ttl 
    for organization in cursor:
        # merging is lead by attribute matching (country, organization type, address), frequency,
        # related persons, documents and software

        merging = False



    cursor = stagingArea.db.aql.execute(
        'FOR doc IN licenses RETURN doc', ttl=1000
    )

    for license in cursor:
        # no merging at entity level for the moment, but the corresponding attribute value which are raw strings 
        # should be matched to entity values

        merging = False
        


    cursor = stagingArea.db.aql.execute(
        'FOR doc IN persons RETURN doc', ttl=3600
    )

    # note: given the possible number of documents, we should rather use pagination than a large ttl 
    for person in cursor:
        # merging based on orcid has already been done on the fly
        # safe merging: same document/software authorship, similar email, same organization relation

        merging = False

        # note: merging based on orcid already done normally

        # check full name
        for person_match in stagingArea.persons.find({'labels': person['labels']}, skip=0):
            # TBD: a post validation here
            if person_match['_key'] == person['_key']:
                continue

                # update/store merging decision list 
                stagingArea.register_merging(person_match, person)
                merging = True

        # TBD the look-up based on 'index_key_name' with a stronger post-validation


    cursor = stagingArea.db.aql.execute(
        'FOR doc IN software RETURN doc', ttl=3600
    )

    # note: given the possible number of documents, we should rather use pagination than a large ttl 
    for software in cursor:
        # we have already merged same software name in the same document
        # other merging: same person in relation, same organization (publisher attribute in mention), 
        # same entity disambiguation, same co-occuring reference, software with same name in closely 
        # related documents, same non trivial version

        merging = False

        software_name = software["label"]



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Disambiguate/conflate entities in the staging area")
    parser.add_argument("--config", default="./config.json", help="path to the config file, default is ./config.json") 

    args = parser.parse_args()
    config_path = args.config

    stagingArea = StagingArea(config_path=config_path)
    stagingArea.init_merging_collections()
    merge(stagingArea)
