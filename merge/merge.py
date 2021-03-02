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
            if 'DOI' in document['metadata']:
                document_match = stagingArea.db.collection('documents').get({'index_doi': document['metadata']['DOI'].lower() })
                if document_match != None:
                    # update/store merging decision list 
                    stagingArea.register_merging(document_match, document)
                    merging = True

        # check title+first_author_last_name matching
        if not merging:
            if 'title' in document['metadata'] and 'author' in document['metadata']:
                local_key = stagingArea.title_author_key(document['metadata']['title'], document['metadata']['author'])
                document_match = stagingArea.db.collection('documents').get({'index_title_author': local_key })
                if document_match != None:
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
        'FOR doc IN persons RETURN doc', ttl=3600
    )

    # note: given the possible number of documents, we should rather use pagination than a large ttl 
    for person in cursor:
        # merging based on orcid has already been done on the fly
        # safe merging: same document/software authorship, similar email, same organization relation

        merging = False


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
