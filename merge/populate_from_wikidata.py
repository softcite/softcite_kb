'''
Populate the staging area graph from Wikidata imported documents
'''

import os
import json
from arango import ArangoClient
from populate_staging_area import StagingArea

def populate(stagingArea):

    database_name_wikidata = "wikidata"

    print("Populate staging area from Wikidata import")
    if not stagingArea.sys_db.has_database(database_name_wikidata):
        print("wikidata import database does not exist: you need to first import Wikidata resources")

    stagingArea.db = stagingArea.client.db(database_name_wikidata, username=stagingArea.config['arango_user'], password=stagingArea.config['arango_pwd'])

    populate_wikidata(stagingArea, stagingArea.get_source(database_name_wikidata))

def populate_wikidata(stagingArea, source_ref):
    '''
    Adding Wikidata resources is straightforward, being already in the right format, but 
    we add the reference source information, and do some direct aggregation based on the explicit 
    CRAN property and reference URL
    '''
    cursor = stagingArea.db.aql.execute(
      'FOR doc IN software RETURN doc', ttl=3600
    )

    for software in cursor:
        # package as software vertex collection

        # for aggregation with R packages, we can check:
        # - programming language (P277) is R (Q206904) 
        # - CRAN project property is P5565, it will relate to the package name (as External identifier type)

        # "depends on software" is P1547

        matched_software = None
        if "claims" in software:
            for key, values in software["claims"].items():
                # insert source reference
                for value in values:
                    if not "references" in value:
                        value["references"] = []
                    value["references"].append(source_ref)

                if key == 'P5565':
                    # CRAN package name
                    for value in values:
                        package_name = value["value"]
                        # try a look-up
                        cursor = stagingArea.software.find({'labels': package_name}, skip=0, limit=1)
                        if cursor.count()>0:
                            matched_software = cursor.next()

                '''
                elif key == 'P856' and matched_software == None:    
                    # official website, which can match with a known official website
                    for value in values:
                        url_name = value["value"]
                '''

        if matched_software != None:
            existing_software = stagingArea.aggregate_with_merge(matched_software, software)
            stagingArea.staging_graph.update_vertex(existing_software)
        else:
            if not stagingArea.staging_graph.has_vertex(software["_id"]):
                stagingArea.staging_graph.insert_vertex("software", software)

    cursor = stagingArea.db.aql.execute(
      'FOR doc IN licenses RETURN doc', ttl=1000
    )

    for license in cursor:
        # licenses are part of a vertex collection, they will be put in relation to work (software)
        # via the edge relation "copyrights"
        
        if "claims" in license:
            for key, values in license["claims"].items():
                # insert source reference
                for value in values:
                    if not "references" in value:
                        value["references"] = []
                    value["references"].append(source_ref)

        if not stagingArea.staging_graph.has_vertex(license["_id"]):
                stagingArea.staging_graph.insert_vertex("licenses", license)

    cursor = stagingArea.db.aql.execute(
      'FOR doc IN organizations RETURN doc', ttl=1000
    )

    for organization in cursor:
        if "claims" in organization:
            for key, values in organization["claims"].items():
                # insert source reference
                for value in values:
                    if not "references" in value:
                        value["references"] = []
                    value["references"].append(source_ref)

        if not stagingArea.staging_graph.has_vertex(organization["_id"]):
                stagingArea.staging_graph.insert_vertex("organizations", organization)

    cursor = stagingArea.db.aql.execute(
      'FOR doc IN publications RETURN doc', ttl=1000
    )

    for publication in cursor:
        if "claims" in publication:
            for key, values in publication["claims"].items():
                # insert source reference
                for value in values:
                    if not "references" in value:
                        value["references"] = []
                    value["references"].append(source_ref)

        publication["_id"] = "documents/" + publication["_key"]

        # we need to add crossref metadata and set the index when possible for further deduplication
        publication = stagingArea.wiki_biblio2json(publication)

        if not stagingArea.staging_graph.has_vertex(publication["_id"]):
            stagingArea.staging_graph.insert_vertex("documents", publication)

    cursor = stagingArea.db.aql.execute(
      'FOR doc IN persons RETURN doc', ttl=1000
    )

    for person in cursor:
        # for persons we match based on orcid at this stage, because it is an explicit
        # strong identifier

        matched_person = None
        if "claims" in person:
            for key, values in person["claims"].items():
                # insert source reference
                for value in values:
                    if not "references" in value:
                        value["references"] = []
                    value["references"].append(source_ref)

                if key == 'P496':
                    # orcid
                    for value in values:
                        orcid = value["value"]
                        # try a look-up
                        cursor = stagingArea.persons.find({'index_orcid': orcid}, skip=0, limit=1)
                        if cursor.count()>0:
                            matched_person = cursor.next()
        if matched_person is None:
            if not stagingArea.staging_graph.has_vertex(person["_id"]):
                stagingArea.staging_graph.insert_vertex("persons", person)
        else:
            person = stagingArea.aggregate_with_merge(matched_person, person)
            stagingArea.staging_graph.update_vertex(person)