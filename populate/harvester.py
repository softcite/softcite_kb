import os
import json
from arango import ArangoClient
import requests
import hashlib

class Harvester(object):

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

    def access_file(self, url, use_cache=True):
        '''
        download file if not cached and use_cache is True
        return local path to the file
        '''
        # check if file is present in the cache
        hash_url = hashlib.md5(url.encode()).hexdigest()
        local_id = 'cache/' + hash_url
        if not use_cache or not self.cache.has(local_id):
            # if not we download the file and save it 
            content, content_type = self.download(url)
            if content == None:
                return none

            self.cache_files = "data/" + self.database_name
            if not os.path.exists(self.cache_files):
                os.makedirs(self.cache_files)

            local_path = os.path.join(self.cache_files, hash_url+"."+content_type)
            with open(local_path, "w") as the_file:
                if content_type == "json":
                    the_file.write(json.dumps(content))
                else:
                    the_file.write(content)

            if use_cache and not self.cache.has(local_id):
                file_json = {}
                file_json['_id'] = local_id
                file_json['path'] = local_path
                self.cache.insert(file_json)
            return local_path
        else:
            # return store path to the file
            file_json = self.cache.get(local_id)
            return file_json["path"]

    def download(self, url):
        response = requests.get(url, allow_redirects=True)
        success = (response.status_code == 200)
        if success:
            content_type = response.headers.get('content-type')
            if "json" in content_type.lower():
                return response.json(), "json"
            elif "html" in content_type.lower():
                return response.content, "html"
            elif "xml" in content_type.lower():
                return response.content, "xml"
            elif "text" in content_type.lower():
                return response.text, "txt"
            else: 
                return response.content, "bin"
        else:
            print("Download of the resource failed with status", response.status_code)
            return None, None