'''
    Common methods for using ArangoDB    
'''

import os
import json
from arango import ArangoClient
import copy

class CommonArangoDB(object):

    database_name = None
    client = None
    cache = None

    # mapping for the source/provenance information
    sources = None

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

        source_path = os.path.join("data", "resources", "sources.json")
        if os.path.isfile(source_path):
            with open(source_path) as f_source:
                self.sources = json.load(f_source)
        else:
            print('Source description json file not found:', source_path)
        

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


    def aggregate_no_merge(self, entity1, entity2):
        '''
        Given two entities to be aggregated:

        1) for statements, add the statements from the second entities as additional statements of the first 
        entity, without any consideration of redundancy. Source information from the two entities are fully 
        preserved in the statements.
        
        2) for non-statement fields, values of the second entities are added to the list in case of list
        value, are added if value is None in the first entity, or ignored if already set in the first entity 
        with non list value.

        The aggregated entity is based on a deep copy of the first entity, which is thus not modified. 
        '''
        result = copy.deepcopy(entity1)
        entity2_ = copy.deepcopy(entity2)

        for key, value in entity2_.items():
            if key == "aliases":
                # append alias if not already there 
                if not "aliases" in result:
                    result["aliases"] = []
                for alias in value:
                    if not "aliases" in entity1 or entity1["aliases"].find(alias) == -1:
                        result["aliases"].append(alias)
            elif key == "summary":
                # only add summary if missing... we might want to manage multiple summaries in the future
                if not "summary" in entity1:
                    result["summary"] = value
            elif key == "descriptions":
                # only add description if missing... we might want to manage multiple description in the future
                if not "descriptions" in entity1:
                    result["descriptions"] = value
            elif key == "claims":
                for the_property, claim in entity2_[key].items():
                    # do we have this property in the first entity ? 
                    if the_property in entity1["claims"]:
                        # if yes add the value to the property entry
                        result["claims"][the_property].append(claim)
                    else:
                        # if no just append it to the claims
                        result["claims"][the_property] = claim
        return result


    def aggregate_with_merge(self, entity1, entity2):
        '''
        Given two entities to be aggregated, 

        1) for statements, add the statements from the second entities as additional statements of the first 
        entity if the prperty value is not present. If present/redundant attribute/value, simply add the 
        the source information from the second entities in this statement.
        
        2) for non-statement fields, values of the second entities are added to the list in case of list
        value, are added if value is None in the first entity, or ignored if already set in the first entity 
        with non list value.

        The aggregated entity is based on a deep copy of the first entity, which is thus not modified. 
        '''
        result = copy.deepcopy(entity1)
        entity2_ = copy.deepcopy(entity2)

        for key, value in entity2_.items():
            if key == "aliases":
                # append alias if not already there 
                if not "aliases" in result:
                    result["aliases"] = []
                for alias in value:
                    if not "aliases" in entity1 or entity1["aliases"].find(alias) == -1:
                        result["aliases"].append(alias)
            elif key == "summary":
                # only add summary if missing... we might want to manage multiple summaries in the future
                if not "summary" in entity1:
                    result["summary"] = value
            elif key == "descriptions":
                # only add description if missing... we might want to manage multiple description in the future
                if not "descriptions" in entity1:
                    result["descriptions"] = value
            elif key == "claims":
                for the_property, claim in entity2_[key].items():
                    # do we have this property in the first entity ? 
                    if the_property in entity1["claims"]:
                        local_merge = False
                        # check if the value are identical by comparing value and data type
                        for the_value in result["claims"][the_property]:
                            local_value = the_value["value"]
                            local_datatype = the_value["datatype"]

                            for the_value2 in entity2["claims"][the_property]:
                                local_value2 = the_value2["value"]
                                local_datatype2 = the_value2["datatype"]

                                if local_value == local_value2 and local_datatype == local_datatype2:
                                    # if yes add we simply add the provenance information the property entry
                                    if not "references" in the_value:
                                        the_value["references"] = []
                                    sources_to_add = the_value2["references"]
                                    for source_to_add in sources_to_add:
                                        the_value["references"].append(source_to_add)
                                    local_merge = True
                                    break
                            if local_merge:
                                break

                        if not local_merge:
                            # if no add the value to the property entry
                            result["claims"][the_property].append(claim)
                    else:
                        # if no just append it to the claims
                        result["claims"][the_property] = claim
        return result

    def get_source(self, database_name):
        '''
        Return source information (provenance) json fragment to be added in the list reference 
        '''
        source = {}
        local_value = {}
        if "wikidata" in self.sources[database_name]:
            local_value["value"] = self.sources[database_name]["wikidata"]
            local_value["datatype"] = "wikibase-item"
        else:
            local_value["value"] = self.sources[database_name]["term"]
            local_value["datatype"] = "string"
        source["P248"] = local_value
        return source