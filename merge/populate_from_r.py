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

    stagingArea.db = stagingArea.client.db(database_name_cran, username=stagingArea.config['arango_user'], password=stagingArea.config['arango_pwd'])
    packages = stagingArea.db.collection('packages')
    set_dependencies(stagingArea, packages)
    

def populate_r(stagingArea, collection):
    relator_file = os.path.join("data", "resources", "relator_code_cran.json")
    if not os.path.isfile(relator_file): 
        print("Error when loading relator code:", relator_file)
        return None

    with open(relator_file) as relator_f:
        relator_code_cran = json.load(relator_f)

    for package in collection:
        # package as software vertex collection
        software = stagingArea.init_entity_from_template("software")
        if software is None:
            raise("cannot init software entity from default template")

        software['labels'] = package['Package']
        # wikidata description are short phrase, so it correspond to R package title, 
        software['descriptions'] = package['Title']
        # for the actual package description, there is no "content summary" property, so we introduce a field "summary"
        software['summary'] = package['Description']
        software['id'] = package['_key']
        software['_key'] = package['_key']
        software['_id'] = "software/" + package['_key']

        if "git_repository" in package:
            local_value = {}
            local_value["value"] = package["git_repository"]
            local_value["datatype"] = "url"
            software["claims"]["P1324"] = []
            software["claims"]["P1324"].append(local_value)

        # programming language (P277) is always R (Q206904) here
        local_value = {}
        local_value["value"] = "Q206904"
        local_value["datatype"] = "wikibase-item"
        software["claims"]["P277"] = []
        software["claims"]["P277"].append(local_value)

        # copyright license is P275
        if "License" in package:
            local_value = {}
            local_value["value"] = package["License"]
            local_value["datatype"] = "string"
            # this will be the object of a further disambiguation to match the license entity
            software["claims"]["P275"] = []
            software["claims"]["P275"].append(local_value)

        # version info (P348)
        if "Version" in package:
            local_value = {}
            local_value["value"] = package["Version"]
            local_value["datatype"] = "string"
            software["claims"]["P348"] = []
            software["claims"]["P348"].append(local_value)

        # official website url is P856 and usuer manual/documentation url is P2078
        # for rOpenSci manual/doc is always with https://docs.ropensci.org/ prefix
        # for CRAN we have a distinct manual field usually pointing to a PDF, 
        # URL being for the official website (or git repo)
        if "Manual" in package:
            local_value = {}
            local_value["value"] = package["Manual"]
            local_value["datatype"] = "url"
            software["claims"]["P2078"] = []
            software["claims"]["P2078"].append(local_value)

        if "URL" in package and len(package["URL"]) > 0:
            for url in package["URL"]:
                local_value = {}
                local_value["value"] = url
                local_value["datatype"] = "url"
                if not "P2078" in software["claims"]:
                    software["claims"]["P2078"] = []
                software["claims"]["P2078"].append(local_value)
        
        stagingArea.staging_graph.insert_vertex("software", software)

        maintainer = None
        if "Maintainer" in package:
            maintainer = package["Maintainer"]

        # authors 
        if "Authors@R" in package:
            for author in package["Authors@R"]:
                maintainer_consumed = process_author(stagingArea, author, software['_key'], relator_code_cran, maintainer)
                if maintainer_consumed:
                    maintainer = None
        elif "Author" in package:
            # author field is relevant only if Authors@R is not 
            for author in package["Author"]:
                maintainer_consumed = process_author(stagingArea, author, software['_key'], relator_code_cran, maintainer)
                if maintainer_consumed:
                    maintainer = None

        
def set_dependencies(stagingArea, collection):
    # this pass will set the dependencies
    for package in collection:
        if not "_hard_deps" in package and not "_soft_deps" in package:
            continue

        # get the first software entry
        cursor = stagingArea.software.find({'labels': package["Package"]}, skip=0, limit=1)
        if cursor.count()>0:
            software1 = cursor.next()
        else:
            continue

        # hard dependencies are edge relations
        if "_hard_deps" in package:
            for dependency in package["_hard_deps"]:
                # relation are via the dependencies edge collection, they relate two software (or packages or libraries)
                # property is "depends on software" (P1547) 
                cursor = stagingArea.software.find({'labels': dependency["package"]}, skip=0, limit=1)
                if cursor.count()>0:
                    software2 = cursor.next()
                    add_dependency(stagingArea, dependency, software1, software2, type="hard")
                else:
                   continue

        # soft dependencies
        if "_soft_deps" in package:
            for dependency in package["_soft_deps"]:
                # relation are via the dependencies edge collection, they relate two software (or packages or libraries)
                # property is "depends on software" (P1547) 
                cursor = stagingArea.software.find({'labels': dependency["package"]}, skip=0, limit=1)
                if cursor.count()>0:
                    software2 = cursor.next()
                    add_dependency(stagingArea, dependency, software1, software2, type="soft")
                else:
                   continue                


def add_dependency(stagingArea, dependency, software1, software2, type=None):
    # relation are via the dependencies edge collection, they relate two software (or packages or libraries)
    # property is "depends on software" (P1547) 
    relation = {}
    relation["claims"] = {}
    relation["claims"]["P1547"] = []
    # add version (P348) if present
    if "version" in dependency:
        local_value = {}
        local_value["value"] = dependency["version"]
        local_value["datatype"] = "string"
        relation["claims"]["P348"] = []
        relation["claims"]["P348"].append(local_value)

    # indicate hard or soft dependencies


    relation["_from"] = software1['_id']

    # find the target dependency software with its unique package name
    relation["_to"] = software2['_id']
    relation["_key"] = software1["_key"] + "_" + software2['_key'] + "_hard"
    relation["_id"] = "dependencies/" + relation["_key"]
    if not stagingArea.staging_graph.has_edge(relation["_id"]):
        stagingArea.staging_graph.insert_edge("dependencies", edge=relation)


def process_author(stagingArea, author, software_key, relator_code_cran, maintainer=None):
    '''
    Process an author in the Author or Author@R fields
    '''
    person = stagingArea.init_entity_from_template("person")
    if person is None:
        raise("cannot init person entity from default template")
    if "full_name" in author:
        person["labels"] = author['full_name']
    elif 'given' in author and 'family' in author:
        if isinstance(author['given'], str):
            person["labels"] = author['given'] + " " + author['family']
        else:
            for giv in author['given']:
                person["labels"] += giv + " "
            person["labels"] += author['family']
    elif 'given' in author:
        person["labels"] = author['given']
    else:
        # there is no name part available
        return None

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
    size = stagingArea.persons.count()
    person["_key"] = "_" + str(size+1)
    person["_id"] = "persons/" + person["_key"]

    stagingArea.staging_graph.insert_vertex("persons", person)

    if "role" in author and isinstance(author["role"], str):
        author["role"] = [ author["role"] ]

    if 'role' in author:
        for role in author["role"]:
            # relation based on role, via the actor edge collection
            if not role in relator_code_cran:
                # try some cleaning
                role = role.replace(")", "")
                role = role.strip("\"")
                if not role in relator_code_cran:
                    print("Error unknown role", role, "defaulting to Contributor")
                    role = "ctb"

            wikidata_property = relator_code_cran[role]["wikidata"]
            set_role(stagingArea, wikidata_property, person, software_key, relator_code_cran[role]["marc_term"].replace(" ", "_"))
    else:
        # role is undefined, we default to contributor (maybe not be the best choice?)
        set_role(stagingArea, relator_code_cran['ctb']["wikidata"], person, software_key, "Contributor")

    if maintainer is None:
        return True

    match = False
    if "full_name" in maintainer:
        if "full_name" in person:
            if maintainer["full_name"] == person["full_name"]:
                match = True
        elif "given" in person:
            if maintainer["full_name"].find(person["given"]) != -1:
                if "family" in person:
                    if maintainer["full_name"].find(person["given"]) != -1:
                        match = True
                else:
                    match = True

    if match == True:
        # if email not present add it
        if "email" in maintainer and not "email" in person:
            person["email"] = maintainer["email"]

        if "full_name" in maintainer and not "full_name" in person:
            person["full_name"] = maintainer["full_name"]

        # add maintainer role, maintained by (P126)
        relation = {}
        relation["claims"] = {}
        relation["claims"]["P126"] = []
        relation["_from"] = "person/" + person["_key"]
        relation["_to"] = "software/" + software_key
        relation["_key"] = person["_key"] + "_" + software_key + "maintainer"
        stagingArea.staging_graph.insert_edge(stagingArea.actor, edge=relation)

        return True

    return False


def set_role(stagingArea, wikidata_property, person, software_key, role_term):
    relation = {}
    relation["claims"] = {}
    relation["claims"][wikidata_property] = []
    relation["_from"] = person["_id"]
    relation["_to"] = "software/" + software_key
    relation["_id"] = "actors/" + person["_key"] + "_" + software_key + "_" + role_term
    stagingArea.staging_graph.insert_edge("actors", edge=relation)
