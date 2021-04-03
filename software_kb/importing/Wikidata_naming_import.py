'''
Only import naming information from wikidata. This is a convenient script for loading separately these
information from a Wikidata dump, without loading the relevant entities themselves. 
'''

import requests
import argparse
import json
from Wikidata_import import Wikidata_harvester
from arango import ArangoClient
import re
from import_common import clean_field, is_git_repo
import sys
import os
import bz2

class Wikidata_naming_harvester(Wikidata_harvester):

    def __init__(self, config_path="./config.yaml", reset=False):
        self.load_config(config_path)
        self.init_naming(reset)

        with open("data/resources/software.wikidata.entities", "rt") as fp:
            for line in fp:
                self.software_list.append(line.rstrip())
        
        self.load_extra_entity_list()

    def import_naming(self, jsonWikidataDumpPath):

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

                if len(line.strip().rstrip('\n')) == 0:
                    # this is usually the end
                    continue

                entityJson = None
                try:
                    entityJson = json.loads(line.rstrip(',\n'))
                except Exception as e:
                    print("Failed to parse json line at line", i, str(e))

                if not entityJson is None:    
                    
                    if self._valid_property(entityJson) or \
                       self._valid_software(entityJson) or \
                       entityJson["id"] in self.persons_list or \
                       entityJson["id"] in self.licenses_list or \
                       entityJson["id"] in self.organizations_list or \
                       entityJson["id"] in self.publications_list:
                        local_labels = entityJson["labels"]
                        if "en" in local_labels:
                            string_name = local_labels["en"]["value"]
                        self.add_naming_wikidata(entityJson["id"], string_name)

        # add the few custom properties
        custom_properties = None
        custom_properties_file = os.path.join("data", "resources", "custom_properties.json")
        if not os.path.isfile(custom_properties_file): 
            print("Warning: no custom Wikidata properties file defintion:", custom_properties_file)
        else:
            with open(custom_properties_file) as properties_f:
                custom_properties_string = properties_f.read()
                custom_properties = json.loads(custom_properties_string)

            for key, value in custom_properties.items():
                self.add_naming_wikidata(key, value['label'])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Import relevant Wikidata entities")
    parser.add_argument("WikidataDumpPath", default=None, help="path to a complete Wikidata JSON dump file in bz2 format") 
    parser.add_argument("--config", default="./config.yaml", help="path to the config file, default is ./config.yaml") 
    parser.add_argument("--reset", action="store_true", help="reset existing collections and re-import all Wikidata records") 

    args = parser.parse_args()
    config_path = args.config
    WikidataDumpPath = args.WikidataDumpPath
    to_reset = args.reset

    if WikidataDumpPath is not None:
        local_harvester = Wikidata_naming_harvester(config_path=config_path, reset=to_reset)
        local_harvester.import_naming(WikidataDumpPath)
    else:
        print("No Wikidata JSON dump file path indicated")

