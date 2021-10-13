import os
import sys
import argparse
from populate_staging_area import StagingArea
from tqdm import tqdm
import logging
import logging.handlers

# default logging settings
logging.basicConfig(filename='merge.log', filemode='w', level=logging.DEBUG)

def merge(stagingArea, reset=False):
    merge_documents(stagingArea, reset)
    merge_organizations(stagingArea, reset)
    merge_licenses(stagingArea, reset)
    merge_persons(stagingArea, reset)
    merge_software(stagingArea, reset)

def merge_documents(stagingArea, reset=False):
    print("\ndocument merging")
    total_results = stagingArea.documents.count()
    page_size = 1000
    nb_pages = (total_results // page_size)+1

    print("entries:", total_results, ", nb. steps:", nb_pages)

    for page_rank in tqdm(range(0, nb_pages)):

        cursor = stagingArea.db.aql.execute(
            'FOR doc IN documents LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) + ' RETURN doc', ttl=3600
        )
    
        for document in cursor:
            # biblio-glutton matching has already been performed, so there is no particular additional 
            # metadata enrichment to be done for document
            
            merging = False

            # check DOI matching
            if 'metadata' in document:
                if 'DOI' in document['metadata'] and len(document['metadata']['DOI'])>0:
                    #print(document['metadata']['DOI'].lower())
                    for document_match in stagingArea.documents.find({'index_doi': document['metadata']['DOI'].lower() }, skip=0):

                        if document_match['_key'] == document['_key']:
                            continue

                        #match_cursor = stagingArea.db.aql.execute(
                        #    "FOR doc IN annotations FILTER doc.document.$oid == '" + local_doc['_key'] + "' RETURN doc", ttl=60
                        #)

                        # update/store merging decision list 
                        success = stagingArea.register_merging(document_match, document)
                        if success:
                            merging = True
                            break

            # check title+first_author_last_name matching
            if not merging:
                if 'title' in document['metadata'] and 'author' in document['metadata']:
                    local_key = stagingArea.title_author_key(document['metadata']['title'], document['metadata']['author'])
                    if local_key != None:
                        for document_match in stagingArea.documents.find({'index_title_author': local_key }, skip=0):

                            if document_match['_key'] == document['_key']:
                                continue

                            # update/store merging decision list 
                            success = stagingArea.register_merging(document_match, document)
                            if success:
                                merging = True
                                break

def merge_organizations(stagingArea, reset=False):
    print("\norganization merging")
    total_results = stagingArea.organizations.count()
    page_size = 1000
    nb_pages = (total_results // page_size)+1

    print("entries:", total_results, ", mb. steps:", nb_pages)

    for page_rank in tqdm(range(0, nb_pages)):

        cursor = stagingArea.db.aql.execute(
            'FOR doc IN organizations LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) + ' RETURN doc', ttl=3600
        )

        # note: given the possible number of documents, we should rather use pagination than a large ttl 
        for organization in cursor:
            # merging is lead by attribute matching (country, organization type, address), frequency,
            # related persons, documents and software

            merging = False


def merge_licenses(stagingArea, reset=False):
    print("\nlicense merging")
    total_results = stagingArea.licenses.count()
    page_size = 1000
    nb_pages = (total_results // page_size)+1

    print("entries:", total_results, ", nb. steps:", nb_pages)

    for page_rank in tqdm(range(0, nb_pages)):

        cursor = stagingArea.db.aql.execute(
            'FOR doc IN licenses LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) + ' RETURN doc', ttl=3600
        )

        for license in cursor:
            # no merging at entity level for the moment, but the corresponding attribute value which are raw strings 
            # should be matched to entity values

            merging = False

        
def merge_persons(stagingArea, reset=False):
    print("\nperson merging")
    total_results = stagingArea.persons.count()
    page_size = 1000
    nb_pages = (total_results // page_size)+1

    print("entries:", total_results, ", nb. steps:", nb_pages)

    for page_rank in tqdm(range(0, nb_pages)):

        cursor = stagingArea.db.aql.execute(
            'FOR doc IN persons LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) + ' RETURN doc', ttl=3600
        )

        for person in cursor:
            # merging based on orcid has already been done on the fly
            # safe merging: same document/software authorship, similar email, same organization relation

            merging = False

            # note: merging based on orcid already done normally

            # check full name
            for person_match in stagingArea.persons.find({'labels': person['labels']}, skip=0):
                if person_match['_key'] == person['_key']:
                    continue

                # TBD: a post validation here

                # update/store merging decision list 
                success = stagingArea.register_merging(person_match, person)
                if success:
                    merging = True
                    break

            # look-up based on 'index_key_name' with a stronger post-validation
            #if not merging:

def merge_software(stagingArea, reset=False):
    print("\nsoftware merging")
    total_results = stagingArea.software.count()
    page_size = 1000
    nb_pages = (total_results // page_size)+1

    print("entries:", total_results, ", nb. steps:", nb_pages)

    for page_rank in tqdm(range(0, nb_pages)):

        cursor = stagingArea.db.aql.execute(
            'FOR doc IN software LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) + ' RETURN doc', ttl=3600
        )

        # note: given the possible number of documents, we should rather use pagination than a large ttl 
        for software in cursor:
            # we have already merged same software name in the same document
            # other merging: same entity disambiguation, 
            # same person in relation, same organization (publisher attribute in mention), 
            # same co-occuring reference, software with same name in closely 
            # related documents, same non trivial version

            merging = False

            # merge by software matching name
            software_name = software["labels"].replace('"', '')
            software_name = software_name.replace("'", "")
            software_name = software_name.replace("'", "")
            #software_name = software_name.replace("\\", "")

            # note: if the length of the the string is too short, it can easily lead to non-meaningful deduplication,
            # but many common framework has such short names (R, Go, C#, etc.). This is depending a lot on the false 
            # positives of software mentions extraction module.

            software_name_variant = _capitalized_variant(software_name)

            # check if software is a R package, programming language (P277) is then R (Q206904) 
            is_R = False
            if "claims" in software and "P277" in software["claims"]:
                for valueBlock in software["claims"]["P277"]:
                    if "value" in valueBlock and valueBlock["value"] == "Q206904":
                        is_R = True
                        break

            if is_R:
                # avoid using aliases because of the frequent port
                aql_query = 'FOR doc IN software FILTER doc.labels == "' + software_name + ' '
                if software_name_variant != None:
                    software_name_variant = software_name_variant.replace('"', '')
                    aql_query += 'OR doc.labels == "' + software_name_variant + ' '
            else:    
                aql_query = 'FOR doc IN software FILTER doc.labels == "' + software_name + '" OR "' + software_name + '" IN doc.aliases '
                if software_name_variant != None:
                    software_name_variant = software_name_variant.replace('"', '')
                    aql_query += 'OR doc.labels == "' + software_name_variant + '" OR "' + software_name_variant + '" IN doc.aliases '
            aql_query += ' RETURN doc'

            try: 
                match_cursor = stagingArea.db.aql.execute(aql_query, ttl=3600)

                for software_match in match_cursor:
                    if software_match['_key'] == software['_key']:
                        continue

                    if not post_validate_merging_software(software, software_match):
                        # post-validation failed
                        continue                    

                    # update/store merging decision list 
                    #print("register...", software_name, software_match['labels'])
                    success = stagingArea.register_merging(software_match, software)
                    if success:
                        merging = True
                        break

                # merge by same disambiguated entity
                if not merging:
                    # do we have a disambiguated entity?
                    local_entity = None
                    if "index_entity" in software:
                        local_entity = software['index_entity']

                    if local_entity != None and local_entity.startswith("Q"): 
                        aql_query = 'FOR doc IN software FILTER doc["index_entity"] == "' + local_entity + '"'
                        aql_query += ' RETURN doc'

                        match_cursor = stagingArea.db.aql.execute(aql_query, ttl=3600)

                        for software_match in match_cursor:
                            if software_match['_key'] == software['_key']:
                                continue

                            # TBD: a post validation here

                            # update/store merging decision list 
                            #print("register...", software_name, software_match['labels'])
                            success = stagingArea.register_merging(software_match, software)
                            if success:
                                merging = True
                                break
            except:
                logging.exception("Failed merging for software document")

def post_validate_merging_software(software, candidate):
    result = False
    target_languages = []
    candidate_languages = []
    '''
    print("--------------------------------------------")
    print(software)
    print(candidate)
    print("--------------------------------------------")
    '''
    # if programming languages are defined, they have to match
    if "P277" in software["claims"]:
        for the_language in software["claims"]["P277"]:
            if "value" in the_language and not the_language["value"] in target_languages:
                target_languages.append(the_language["value"])

    if "P277" in candidate["claims"]:
        for the_language in candidate["claims"]["P277"]:
            if "value" in the_language and not the_language["value"] in candidate_languages:
                candidate_languages.append(the_language["value"])

    if len(target_languages) > 0 and len(candidate_languages) > 0:
        for language in target_languages:
            if language in candidate_languages:
                result = store_true
    
    if len(target_languages) == 0 or len(candidate_languages) == 0:
        result = True
    # note: otherwise we could also check local context for language indication, e.g. "R package" (Q206904)
    return result

def _capitalized_variant(term):
    '''
    For a term all upper-cased, generate the term variant with only first letter of term components upper-cased
    '''
    if not term.isupper():
        return None

    term_variant = ''
    start = True
    for c in term:
        if start:
            start = False
            term_variant += c
        else:
            if c == ' ' or c == '-':
                start = True
                term_variant += c
            else:
                term_variant += c.lower()
    return term_variant

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Disambiguate/conflate entities in the staging area")
    parser.add_argument("--config", default="./config.yaml", help="path to the config file, default is ./config.yaml") 

    args = parser.parse_args()
    config_path = args.config

    stagingArea = StagingArea(config_path=config_path)
    stagingArea.init_merging_collections()
    merge(stagingArea)
