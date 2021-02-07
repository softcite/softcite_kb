import os
import json
from arango import ArangoClient
import requests
import hashlib
import time
from random import randint, seed

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
        
        seed(1)

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
            content, extension, status = self.download(url)
            if content == None:
                # online access failed
                if status == 404:
                    # resources is not present, we can store this result in the cache to avoid new calls
                    if use_cache and not self.cache.has(local_id):
                        file_json = {}
                        file_json['_id'] = local_id
                        file_json['path'] = None
                        self.cache.insert(file_json)
                return None

            self.cache_files = "data/" + self.database_name
            if not os.path.exists(self.cache_files):
                os.makedirs(self.cache_files)

            local_path = os.path.join(self.cache_files, hash_url+"."+extension)

            if extension == "txt" or extension == "xml":
                with open(local_path, "w") as the_file:
                    the_file.write(content)
            elif extension == "json":   
                with open(local_path, "w") as the_file:
                    the_file.write(json.dumps(content))
            else: 
                # keep binary, in particular for html
                with open(local_path, "wb") as the_file:
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
        time.sleep(randint(1, 2))
        user_agent = {'User-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:68.0) Gecko/20100101 Firefox/68.0'}
        success = False
        response = None
        try:
            response = requests.get(url, allow_redirects=True, headers=user_agent)
            success = (response.status_code == 200)
            print(url, response.status_code, response.headers.get('content-type'))
        except:
            print("Connection fails:", url)
        if success:
            content_type = response.headers.get('content-type')
            print(content_type)
            extension = "bin"
            if content_type == None:
                content_type = "text"
                extension = "text"
            if "json" in content_type.lower():
                return response.json(), "json", response.status_code
            elif "html" in content_type.lower():
                # html is kept non-decoded to deal with encoding issue at later stage
                return response.content, "html", response.status_code
            elif "xml" in content_type.lower():
                return response.content, "xml", response.status_code
            elif "text" in content_type.lower():
                return response.text, "txt", response.status_code
            else: 
                return response.content, extension, response.status_code
        else:
            status = 0
            if response is not None:
                print("Download of the resource failed with status", response.status_code)
                status = response.status_code
            else:
                print("Download of the resource failed with connection error, remote disconnected?")   
            return None, None, status