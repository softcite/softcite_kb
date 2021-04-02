'''
    Common methods for using ArangoDB    
'''

import os
import json
import yaml
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

    def load_config(self, config_file='./config.yaml'):
        """
        Load the json configuration 
        """
        if config_file and os.path.exists(config_file) and os.path.isfile(config_file):
            with open(config_file, 'r') as the_file:
                raw_configuration = the_file.read()

            try:
                configuration = yaml.safe_load(raw_configuration)
            except:
                # note: it appears complicated to get parse error details from the exception
                configuration = None

            if configuration == None:
                msg = "Error: yaml config file cannot be parsed: " + str(config_file)
                raise Exception(msg)
        else:
            msg = "Error: configuration file is not valid: " + str(config_file)
            raise Exception(msg)

        self.config = configuration

        # check ArangoDB availability
        if not self.validate_arangodb_conn_params(): 
            print('Connection to ArangoDb not possible, please review the information in the config file', path)
            return

        # Connect to "_system" database as user indicated in the config
        try:
            # Initialize the client for ArangoDB
            self.client = ArangoClient(hosts=self.config['arangodb']['arango_protocol']+"://"+self.config['arangodb']['arango_host']+':'+str(self.config['arangodb']['arango_port']))
            self.sys_db = self.client.db('_system', username=self.config['arangodb']['arango_user'], password=self.config['arangodb']['arango_pwd'])
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
        
        if not 'arangodb' in self.config:
            # missing ArangoDB settings block
            return False

        if not 'arango_host' in self.config['arangodb']:
            print("ArangoDB host information not provided in config file")
            valid_conn_params = False
        
        if not 'arango_port' in self.config['arangodb']:
            print("ArangoDB port information not provided in config file")
            valid_conn_params = False
        
        if not 'arango_protocol' in self.config['arangodb']:
            print("ArangoDB connection protocol not provided in config file")
            valid_conn_params = False
        
        if not 'arango_user' in self.config['arangodb']:
            print("User name for ArangoDb not provided in config file")
            valid_conn_params = False
        
        if not 'arango_pwd' in self.config['arangodb']:
            print("Password for ArangoDb user not provided in config file")
            valid_conn_params = False
        
        return valid_conn_params

    def init_naming(self, reset=False):
        # we store the naming key-value in a distinct database (not sure it's the best)
        # create database and collection
        if not self.sys_db.has_database("naming"):
            self.sys_db.create_database("naming")

        self.naming_db = self.client.db("naming", username=self.config['arangodb']['arango_user'], password=self.config['arangodb']['arango_pwd'])

        if reset:
            if self.naming_db.has_collection('naming_wikidata'):
                self.naming_db.delete_collection('naming_wikidata')

        # naming key-value store... it's actually simply a collection with a unique key per document
        if not self.naming_db.has_collection('naming_wikidata'):
            self.naming_wikidata = self.naming_db.create_collection('naming_wikidata')
            # we add an index to get the identifier back from the canonical string
            self.index_reverse_name = self.naming_wikidata.add_hash_index(fields=['value'], unique=True, sparse=False)
        else:
            self.naming_wikidata = self.naming_db.collection('naming_wikidata')

    def naming_wikidata_string(self, wikidata_id):
        # wikidata id -> canonical string
        if not wikidata_id.startswith("P") and not wikidata_id.startswith("Q"):
            return None

        if wikidata_id in self.naming_wikidata:
            return self.naming_wikidata[wikidata_id]["value"]
        else:
            return None

    def naming_wikidata_id(self, string):
        # canonical string -> wikidata id
        cursor = self.naming_wikidata.find({'value': string}, skip=0, limit=1)
        if cursor.has_more():
            result = cursor.next()
            return result['_key']
        else:
            return None

    def add_naming_wikidata(self, wikidata_id, string):
        # check if the entry if not already present
        if wikidata_id in self.naming_wikidata and self.naming_wikidata[wikidata_id]["value"] == string:
            # nothing to do
            return

        # check string uniqueness
        try:
            cursor = self.naming_wikidata.find({'value': string}, skip=0, limit=1)
            if cursor.has_more():
                raise Exception("error adding Wikidata ID mapping: the target string is not unique")
        except:
            print("Invalid target string key:", string)

        if wikidata_id in self.naming_wikidata:
            self.naming_wikidata[wikidata_id] = { "_key": wikidata_id, "value": string }
        else:
            try:
                self.naming_wikidata.insert({ "_key": wikidata_id, "value": string })
            except:
                print("Invalid key:", string)    
  
    def remove_naming_wikidata(self, wikidata_id):
        if not wikidata_id in self.naming_wikidata:
            # do nothing
            return

        self.naming_wikidata.delete(wikidata_id)

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
                        result["claims"][the_property].extend(claim)
                    else:
                        # if no just append it to the claims
                        result["claims"][the_property] = claim
            elif key.startswith("index_"):
                # have an index field that we can copy if not present in the first entity
                if not key in entity1:
                    result[key] = value
            elif key == "metadata":
                if not "metadata" in entity1:
                    result["metadata"] = metadata
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
                    if not "aliases" in entity1 or not alias in entity1["aliases"]:
                        result["aliases"].append(alias)
            elif key == "summary":
                # only add summary if missing... we might want to manage multiple summaries in the future
                if not "summary" in entity1 or len(entity1["summary"]) == 0:
                    result["summary"] = value
            elif key == "descriptions":
                # only add description if missing... we might want to manage multiple description in the future
                if not "descriptions" in entity1 or len(entity1["descriptions"]) == 0:
                    result["descriptions"] = value
            elif key == "claims":
                for the_property, claim in entity2_[key].items():
                    # do we have this property in the first entity ? 
                    if the_property in entity1["claims"]:
                        # check if the new values for this property are identical by comparing value and data type
                        for the_value2 in claim:
                            local_value2 = the_value2["value"]
                            local_datatype2 = the_value2["datatype"]
                            local_merge = False
                            '''
                            i = 0
                            for the_value in entity1["claims"][the_property]:
                                local_value = the_value["value"]
                                local_datatype = the_value["datatype"]

                                if local_value == local_value2 and local_datatype == local_datatype2:
                                    # if yes add we simply add the provenance information the property entry
                                    
                                    # this is the value in the newly build merge entity
                                    the_new_value = result["claims"][the_property][i]

                                    if not "references" in the_new_value:
                                        the_new_value["references"] = []
                                    sources_to_add = the_value2["references"]
                                    for source_to_add in sources_to_add:
                                        add_ref_if_not_present(the_new_value["references"], source_to_add)
                                    local_merge = True
                                    break
                                i += 1
                            '''
                            for the_value in result["claims"][the_property]:
                                local_value = the_value["value"]
                                local_datatype = the_value["datatype"]

                                if local_value == local_value2 and local_datatype == local_datatype2:
                                    # if yes add we simply add the provenance information the property entry

                                    if not "references" in the_value:
                                        the_value["references"] = []
                                    sources_to_add = the_value2["references"]
                                    for source_to_add in sources_to_add:
                                        add_ref_if_not_present(the_value["references"], source_to_add)
                                    local_merge = True
                                    break

                            if not local_merge:
                                # if no merge, add the value to the property entry
                                result["claims"][the_property].append(the_value2)
                            
                    else:
                        # if no just append it to the other claims
                        result["claims"][the_property] = claim
            elif key.startswith("index_"):
                # have an index field that we can copy if not present in the first entity
                if not key in entity1:
                    result[key] = value
            elif key == "metadata":
                if not "metadata" in entity1:
                    result["metadata"] = metadata
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

def add_ref_if_not_present(references, ref_to_add):
    '''
    check if a reference entry is not already present in a reference list:
    - if no, add it to the list
    - if yes, increase origin count to keep track of the number of times the same source is claiming the same fact
    '''
    found = False
    value_to_add = None
    for key, value in ref_to_add.items():
        value_to_add = value["value"]

    if value_to_add == None:
        return references

    for reference in references:
        for key, value in reference.items():
            if "value" in value and value["value"] == value_to_add:
                found = True
                # increase count attribute (no count attribute means count == 1)
                if "count" in value:
                    value["count"] += 1
                else:
                    value["count"] = 2
                break
        if found:
            break

    if not found or len(references) == 0:
        references.append(ref_to_add)        

    return references

def simplify_entity(jsonEntity):
    """
    As we focus on English (at least for the moment), we ignore other language fields 
    """
    _replace_element(jsonEntity, "labels", "en")
    _replace_element(jsonEntity, "descriptions", "en")
    _replace_element(jsonEntity, "aliases", "en")

    if 'sitelinks' in jsonEntity:
        del jsonEntity['sitelinks']

    # remove language levels because we restrict to English only currently
    if "descriptions" in jsonEntity:
        if "en" in jsonEntity["descriptions"]:
            jsonEntity["descriptions"] = jsonEntity["descriptions"]["en"]["value"]
    
    if "labels" in jsonEntity:
        if "en" in jsonEntity["labels"]:    
            jsonEntity["labels"] = jsonEntity["labels"]["en"]["value"]

    if "aliases" in jsonEntity:
        if "en" in jsonEntity["aliases"]:
            all_aliases = []
            for alias in jsonEntity["aliases"]["en"]:
                all_aliases.append(alias["value"])
            jsonEntity["aliases"] = all_aliases
        else:
            jsonEntity["aliases"] = []

    # note: we also have some property of datatype "monolingualtext" introducing language information 
    # this will be preserved because not reversible

    # simplifying the "snark" as "value" attribute
    if "claims" in jsonEntity:
        properties_to_be_removed = []
        for wikidata_property in jsonEntity["claims"]:
            new_statements = []
            for statement in jsonEntity["claims"][wikidata_property]:
                new_statement = {}
                if not "datavalue" in statement["mainsnak"]:
                    continue
                datavalue = statement["mainsnak"]["datavalue"]
                new_statement["value"] = datavalue["value"]
                new_statement["datatype"] = statement["mainsnak"]["datatype"]
                # simplify the value based on the datatype
                the_value = new_statement["value"]
                if new_statement["datatype"] == "wikibase-item":
                    del the_value["numeric-id"]
                    del the_value["entity-type"]
                    new_statement["value"] = datavalue["value"]["id"]
                elif new_statement["datatype"] == "time":
                    del the_value["before"]
                    del the_value["timezone"]
                    del the_value["calendarmodel"]
                    del the_value["after"]
                    del the_value["precision"]
                new_statements.append(new_statement)
            if len(new_statements) > 0:
                jsonEntity["claims"][wikidata_property] = new_statements
            else:
                properties_to_be_removed.append(wikidata_property)

        for wikidata_property in properties_to_be_removed:
            del jsonEntity["claims"][wikidata_property]

    if "lastrevid" in jsonEntity:
        del jsonEntity["lastrevid"]

    if "type" in jsonEntity:
        del jsonEntity["type"]

    return jsonEntity
                
def _replace_element(jsonEntity, element, lang):
    if element in jsonEntity:
        if lang in jsonEntity[element]:
            en_lab_val = jsonEntity[element][lang]
            en_lab = {}
            en_lab[lang] = en_lab_val
            jsonEntity[element] = en_lab
    return jsonEntity