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

    populate_r(stagingArea, packages)

def populate_r(stagingArea, collection):
    for package in collection:
        print(package['Package'])
