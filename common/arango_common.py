'''
    Common methods for using ArangoDB    
'''

import os
import json
from arango import ArangoClient

class CommonArangoDB(object):

    database_name = None
    client = None
    cache = None

    # naming is a common key-value store to map Wikidata identifiers to canonical strings
    # for readability purposes 
    naming_wikidata = None

    def load_config(self, path='./config.json'):
        """
        Load the json configuration 
        """
        config_json = open(path).read()
        self.config = json.loads(config_json)

        # check ArangoDB availability
        if not self.validate_arangodb_conn_params(): 
            print('Connection to ArangoDb not possible, please review the information in the config file', path)
            return

        # Connect to "_system" database as user indicated in the config
        try:
            # Initialize the client for ArangoDB
            self.client = ArangoClient(hosts=self.config['arango_protocol']+"://"+self.config['arango_host']+':'+str(self.config['arango_port']))
            self.sys_db = self.client.db('_system', username=self.config['arango_user'], password=self.config['arango_pwd'])
        except:
            print('Connection to ArangoDb failed')

    def validate_arangodb_conn_params(self):
        valid_conn_params = True
        
        if not 'arango_host' in self.config:
            print("ArangoDB host information not provided in config file")
            valid_conn_params = False
        
        if not 'arango_port' in self.config:
            print("ArangoDB port information not provided in config file")
            valid_conn_params = False
        
        if not 'arango_protocol' in self.config:
            print("ArangoDB connection protocol not provided in config file")
            valid_conn_params = False
        
        if not 'arango_user' in self.config:
            print("User name for ArangoDb not provided in config file")
            valid_conn_params = False
        
        if not 'arango_pwd' in self.config:
            print("Password for ArangoDb user not provided in config file")
            valid_conn_params = False
        
        return valid_conn_params

    def init_naming(self):
        # we store the naming key-value in a distinct database (not sure it's the best)
        # create database and collection
        if not self.sys_db.has_database("naming"):
            self.sys_db.create_database("naming")

        self.naming_db = self.client.db("naming", username=self.config['arango_user'], password=self.config['arango_pwd'])

        # naming key-value store... it's actually simply a collection with a unique key per document
        if not self.naming_db.has_collection('naming_wikidata'):
            self.naming_wikidata = self.naming_db.create_collection('naming_wikidata')
        else:
            self.naming_wikidata = self.naming_db.collection('naming_wikidata')

        # we maintain a synchronized reverse mapping, in particular to ensure a unique string for a wikidata id 
        if not self.naming_db.has_collection('naming_reverse_wikidata'):
            self.naming_reverse_wikidata = self.naming_db.create_collection('naming_reverse_wikidata')
        else:
            self.naming_reverse_wikidata = self.naming_db.collection('naming_reverse_wikidata')

    def naming_wikidata_string(self, wikidata_id):
        # wikidata id -> canonical string
        if wikidata_id in self.naming_wikidata:
            return self.naming_wikidata[wikidata_id]
        else:
            return None

    def naming_wikidata_id(self, string):
        # canonical string -> wikidata id
        if string in self.naming_reverse_wikidata:
            return self.naming_reverse_wikidata[string]
        else:
            return None

    def add_naming_wikidata(self, wikidata_id, string):
        # check if the entry if not already present
        if wikidata_id in self.naming_wikidata and self.naming_wikidata[wikidata_id] == string:
            # nothing to do
            return

        # check string uniqueness
        if string in self.naming_reverse_wikidata:
            raise Exception("error adding Wikidata ID mapping: the target string is not unique")

        if wikidata_id in self.naming_wikidata:
            self.naming_wikidata[wikidata_id] = string
        else:
            self.naming_wikidata.insert({wikidata_id: string})

        self.naming_reverse_wikidata.insert({string:wikidata_id})

    def remove_naming_wikidata(self, wikidata_id):
        if not wikidata_id in self.naming_wikidata:
            # do nothing
            return

        string = self.naming_wikidata[wikidata_id]
        self.naming_wikidata.delete(wikidata_id)
        if string in self.naming_reverse_wikidata:
            self.naming_reverse_wikidata.delete(string)


    def normalize_naming_string(string):
        '''
        As the string is identifier in the reverse mapping, we have to ensure a valid key form for ArangoDB
        see https://www.arangodb.com/docs/stable/data-modeling-naming-conventions-document-keys.html
        '''
        string = string.replace("/", "%%")
        return string

    def recover_naming_string(string):
        string = string.replace("%%", "/")
        return string
