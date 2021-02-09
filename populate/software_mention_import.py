'''
    Import software mentions extracted by the Grobid module ourresearch/software-mentions

    This is realized via the MongoDB JSON export where every mention objects are written. Three collections
    are available: mentions, documents (documents where the mention is extracted) and references 
    (bibliographical references part of the context and attached to the extracted mentioned software)

'''

import requests
import argparse
import json
from harvester import Harvester
from arango import ArangoClient
import re


class Software_mention_import(Harvester):

    database_name = "mentions"

    def __init__(self, config_path="./config.json"):
        self.load_config(config_path)

        # create database and collection
        if not self.sys_db.has_database(self.database_name):
            self.sys_db.create_database(self.database_name)

        self.db = self.client.db(self.database_name, username=self.config['arango_user'], password=self.config['arango_pwd'])

        if not self.db.has_collection('annotations'):
            self.annotations = self.db.create_collection('annotations')
        else:
            self.annotations = self.db.collection('annotations')

        if not self.db.has_collection('documents'):
            self.documents = self.db.create_collection('documents')
        else:
            self.documents = self.db.collection('documents')

        if not self.db.has_collection('references'):
            self.references = self.db.create_collection('references')
        else:
            self.references = self.db.collection('references')

    def import_mentions(self, mongoExportPath, reset=False):
        '''
        we use the result of mongoexport, one JSON per line, with one file per collection
        ''' 
        if reset:
            self.db.delete_collection('annotations')
            self.annotations = self.db.create_collection('annotations')

            self.db.delete_collection('documents')
            self.documents = self.db.create_collection('documents')

            self.db.delete_collection('references')
            self.references = self.db.create_collection('references')

        


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Import collection of automatically extracted software mention")
    parser.add_argument("mongoExportPath", default=None, help="path to the repository with MongoDB JSON export containing the software mentions") 
    parser.add_argument("--config", default="./config.json", help="path to the config file, default is ./config.json") 
    parser.add_argument("--reset", action="store_true", help="reset existing collections and re-import all software mention records") 

    args = parser.parse_args()
    config_path = args.config
    mongoExportPath = args.mongoExportPath
    to_reset = args.reset

    if mongoExportPath is not None:
        local_harvester = Software_mention_import(config_path=config_path)
        local_harvester.import_mentions(mongoExportPath, reset=to_reset)
    else:
        print("No MongoDB export directory path indicated")

