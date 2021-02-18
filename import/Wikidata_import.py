'''
    Import Wikidata entities corresponding to software in the Knowledge Base

    This is realized from the JSON Wikidata dump. Entities corresponding to software (except video games) are 
    imported to seed the KB, together with some relevant entities in relation to software corresponding to 
    persons, organizations and close concepts (programming language, OS, license). 

    A recent full Wikidata json dump compressed with bz2 (which is more compact) is needed, which 
    can be dowloaded [here](https://dumps.wikimedia.org/wikidatawiki/entities/). There is no need to 
    uncompressed the json dump.
'''

import requests
import argparse
import json
from harvester import Harvester
from arango import ArangoClient
import re
from import_common import clean_field, is_git_repo
import sys
import os
import bz2

class Wikidata_harvester(Harvester):

    database_name = "wikidata"

    def __init__(self, config_path="./config.json"):
        self.load_config(config_path)
        self.init_naming()

        # create database and collection
        if not self.sys_db.has_database(self.database_name):
            self.sys_db.create_database(self.database_name)

        self.db = self.client.db(self.database_name, username=self.config['arango_user'], password=self.config['arango_pwd'])

        if not self.db.has_collection('software'):
            self.software = self.db.create_collection('software')
        else:
            self.software = self.db.collection('software')

        if not self.db.has_collection('cache'):
            self.cache = self.db.create_collection('cache')
        else:
            self.cache = self.db.collection('cache')

        # list of valid entities (this is relatively small, but we might want to use a key/value store, 
        # like LMDB map, in the future)
        self.entities = []
        with open("data/resources/software.wikidata.entities", "rt") as fp:
            for line in fp:
                self.entities.append(line.rstrip())

    def import_entities(self, jsonWikidataDumpPath, reset=False):
        if reset:
            self.db.delete_collection('software')
            self.software = self.db.create_collection('software')

        name_additional_entities = []

        # read compressed dump line by line
        print(jsonWikidataDumpPath)
        with bz2.open(jsonWikidataDumpPath, "rt") as bzinput:
            bzinput.read(2) # skip first 2 bytes 
            for i, line in enumerate(bzinput):
                if i % 1000000 == 0 and i != 0:
                    sys.stdout.write(str(i))
                    sys.stdout.flush()
                elif i % 100000 == 0 and i != 0:
                    sys.stdout.write('.')
                    sys.stdout.flush()
                try:
                    if len(line.strip()) == 0:
                        # this is usually the end
                        continue

                    entityJson = json.loads(line.rstrip(',\n'))
                    if self._valid_entity(entityJson):
                        entityJson = self._simplify(entityJson)
                        # store entity in arangodb as document
                        local_id = entityJson['id']
                        if not self.software.has(local_id):
                            entityJson['_id'] = 'software/' + local_id
                            self.software.insert(entityJson)
                    if self._valid_property(entityJson):
                        local_labels = entityJson["labels"]
                        if "en" in local_labels:
                            string_name = local_labels["en"]["value"]
                        self.add_naming_wikidata(entityJson["id"], string_name)
                except Exception as e:
                    print("Failed to parse json line at line", i, str(e))
                    #print("Failed to parse json line at line", i, "json content:", line.rstrip(',\n'))

    def _valid_entity(self, jsonEntity):
        """
        Filter out json wikidata entries not relevant to software. For this we use an external
        list of entities produced by entity-fishing, which has a full KB representation for 
        exploiting hierarchy of P31 and P279 properties. Wikidata identifiers are stable. 

        We also import all properties. 
        """
        if jsonEntity["id"] in self.entities:
            return True
        else:
            return False 

    def _valid_property(self, jsonEntity):
        """
        We have a limited number of properties (still a few thousands though), but we can also import all of them. 
        """
        if jsonEntity["id"].startswith("P"):
            return True
        else:
            return False 

    def _simplify(self, jsonEntity):
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Import relevant Wikidata entities")
    parser.add_argument("WikidataDumpPath", default=None, help="path to a complete Wikidata JSON dump file in bz2 format") 
    parser.add_argument("--config", default="./config.json", help="path to the config file, default is ./config.json") 
    parser.add_argument("--reset", action="store_true", help="reset existing collections and re-import all Wikidata records") 

    args = parser.parse_args()
    config_path = args.config
    WikidataDumpPath = args.WikidataDumpPath
    to_reset = args.reset

    if WikidataDumpPath is not None:
        local_harvester = Wikidata_harvester(config_path=config_path)
        local_harvester.import_entities(WikidataDumpPath, reset=to_reset)
    else:
        print("No Wikidata JSON dump file path indicated")

