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
