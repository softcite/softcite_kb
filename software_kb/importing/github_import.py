'''
    Access, convert and load GitHub relevant public data

    See REST API at https://docs.github.com/en/rest
'''

import requests
import argparse
import json
from harvester import Harvester
from arango import ArangoClient
import re
from collections import OrderedDict

base_url = "hhttps://api.github.com/"

class rOpenSci_harvester(Harvester):

    database_name = "GitHub"

    def __init__(self, config_path="./config.yaml"):
        self.load_config(config_path)

        # create database and collection
        if not self.sys_db.has_database(self.database_name):
            self.sys_db.create_database(self.database_name)

        self.db = self.client.db(self.database_name, username=self.config['arangodb']['arango_user'], password=self.config['arangodb']['arango_pwd'])

        if not self.db.has_collection('users'):
            self.users = self.db.create_collection('users')
        else:
            self.users = self.db.collection('users')

        if not self.db.has_collection('repos'):
            self.repos = self.db.create_collection('repos')
        else:
            self.repos = self.db.collection('repos')

        if not self.db.has_collection('cache'):
            self.cache = self.db.create_collection('cache')
        else:
            self.cache = self.db.collection('cache')

