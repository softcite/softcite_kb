'''
Populate the staging area graph from CRAN and rOpenSci imported documents
'''

import os
import json
from arango import ArangoClient
from populate_staging_area import StagingArea

database_name_rOpenSci = "rOpenSci"
database_name_cran = "CRAN" 

def populate(stagingArea):

    # rOpenSci
    if not stagingArea.sys_db.has_database(database_name_rOpenSci):
        print("rOpenSci import database does not exist: you need to first import rOpenSci resources")

    stagingArea.db = stagingArea.client.db(database_name_rOpenSci, username=stagingArea.config['arango_user'], password=stagingArea.config['arango_pwd'])
    packages = stagingArea.db.collection('packages')

    populate_r(stagingArea, packages)

    # CRAN
    if not stagingArea.sys_db.has_database(database_name_cran):
        print("CRAN import database does not exist: you need to first import CRAN resources")

    stagingArea.db = stagingArea.client.db(database_name_cran, username=stagingArea.config['arango_user'], password=stagingArea.config['arango_pwd'])
    packages = stagingArea.db.collection('packages')

    # we set the dependencies in a second pass, having all the packages entities put in relation now set
    stagingArea.db = stagingArea.client.db(database_name_rOpenSci, username=stagingArea.config['arango_user'], password=stagingArea.config['arango_pwd'])
    packages = stagingArea.db.collection('packages')
    set_dependencies(stagingArea, packages)

    stagingArea.db = stagingArea.client.db(database_name_rOpenSci, username=stagingArea.config['arango_user'], password=stagingArea.config['arango_pwd'])
    packages = stagingArea.db.collection('packages')
    set_dependencies(stagingArea, packages)

def populate_r(stagingArea, collection):
    relator_file = os.path.join("resources", "relator_code_cran.json")
    if not os.path.isfile(relator_file): 
        print("Error when loading relator code:", relator_file)
        return None

    with open() as template_file:
        relator_code_cran = json.loads(relator_file)

    for package in collection:
        # package as software vertex collection
        software = stagingArea.init_entity_from_template("software")
        software['labels'] = package['Package']
        # wikidata description are short phrase, so it correspond to R package title, 
        software['descriptions'] = package['Title']
        # for the actual package description, there is no "content summary" property, so we introduce a field "summary"
        software['summary'] = package['Description']
        software['id'] = package['_id']
        software['_id'] = package['_id']

        # authors 
        if "Authors@R" in package:
            for author in package["Authors@R"]:
                process_author(author)
        elif "Author" in package:
            # author field is relevant only if Authors@R is not 
            for author in package["Authors"]:
                process_author(author)

        if "git_repository" in package:
            local_value = {}
            local_value["value"] = package["git_repository"]
            local_value["datatype"] = "url"
            software["claims"]["P1324"] = []
            software["claims"]["P1324"].append(local_value)

        # programming language (P277) is R (Q206904)
        local_value = {}
        local_value["value"] = "Q206904"
        local_value["datatype"] = "wikibase-item"
        software["claims"]["P277"] = []
        software["claims"]["P277"].append(local_value)

        # copyright license is P275
        local_value = {}
        local_value["value"] = package["License"]
        local_value["datatype"] = "string"
        # this will be the object of a further disambiguation to match the license entity
        software["claims"]["P275"] = []
        software["claims"]["P275"].append(local_value)

        # version info (P348)
        local_value = {}
        local_value["value"] = package["P348"]
        local_value["datatype"] = "string"
        software["claims"]["P348"] = []
        software["claims"]["P348"].append(local_value)

        # official website url is P856 and usuer manual/documentation url is P2078
        # for rOpenSci manual/doc is always with https://docs.ropensci.org/ prefix
        # for CRAN we have a distinct manual field usually pointing to a PDF, 
        # URL being for the official website (or git repo)
        
        

def set_dependencies(stagingArea, collection):
    # this pass will set the dependencies
    for package in collection:

        # hard dependencies are edge relations

        for dependency in package["_hard_deps"]:
            # relation are via the dependencies edge collection, they relate two software (or packages or libraries)
            relation = {}
            relation[wikidata_property] = []
            local_value = {}
            local_value["value"] = software['_id']
            local_value["datatype"] = "wikibase-item"
            relation[wikidata_property].append()
            relation["from"] = "software/" + software["_id"]

            # find the target dependency software with its unique package name

            results = stagingArea.software.find({'labels': dependency["package"]}, skip=0, limit=1)

            software2 = results[0]

            relation["to"] = "software/" + software2['_id']




def process_author(author):
    '''
    Process an author in the Author or Author@R fields
    '''
    person = stagingArea.init_entity_from_template("person")
    if "full_name" in author:
        person["labels"] = author['full_name']
    elif 'given' in author and 'family' in author:
        person["labels"] = author['given'] + " " + author['family']
    elif 'given' in author:
        person["labels"] = author['given']

    if 'given' in author:
        # "given name" -> P735
        local_value = {}
        local_value["value"] = author['given']
        local_value["datatype"] = "string"
        person["claims"]["P735"] = []
        person["claims"]["P735"].append(local_value)
        
    if 'family' in author:
        # "family name" -> P734
        local_value = {}
        local_value["value"] = author['family']
        local_value["datatype"] = "string"
        person["claims"]["P734"] = []
        person["claims"]["P734"].append(local_value)

    if 'orcid' in author:
        # P496
        local_value = {}
        local_value["value"] = author['orcid']
        local_value["datatype"] = "external-id"
        person["claims"]["P496"] = []
        person["claims"]["P496"].append(local_value)

    if 'email' in author:
        # P968
        local_value = {}
        local_value["value"] = author['email']
        local_value["datatype"] = "url"
        person["claims"]["P968"] = []
        person["claims"]["P968"].append(local_value)

    # github identifier P2037
    # Google Scholar author ID P1960

    # if only full_name is available, we need grobid to further parse the name

    stagingArea.staging_graph.insert_vertex(stagingArea.persons, person)

    for role in author["roles"]:
        # relation based on role, via the actor edge collection
        wikidata_property = relator_code_cran[role]["wikidata"]
        if wikidata_property is not None and len(wikidata_property) > 0:
            relation = {}
            relation["claims"] = {}
            relation["claims"][wikidata_property] = []
            relation["from"] = "person/" + person["_id"]
            relation["to"] = "software/" + software['_id']
            relation["_key"] = person["_id"] + "_" + software['_id'] + relator_code_cran[role]["marc_term"]
            stagingArea.staging_graph.insert_edge(stagingArea.actor, edge=relation)

