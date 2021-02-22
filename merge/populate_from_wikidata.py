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
    entities = stagingArea.db.collection('software')

    populate_wikidata(stagingArea, entities, stagingArea.get_source(database_name_wikidata))

def populate_wikidata(stagingArea, collection, source_ref):
    '''
    Adding Wikidata resources is straightforward, being already in the right format, but 
    we add the reference source information, and do some direct aggregation based on the explicit 
    CRAN property and reference URL
    '''
    cursor = stagingArea.db.aql.execute(
      'FOR doc IN software RETURN doc', ttl=1000
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
