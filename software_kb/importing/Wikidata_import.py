'''
    Import Wikidata entities corresponding to software in the Knowledge Base

    This is realized from the JSON Wikidata dump. Entities corresponding to software (except video games) are 
    imported to seed the KB, together with some relevant entities in relation to software corresponding to 
    persons, organizations and close concepts (programming language, OS, license). 

    A recent full Wikidata json dump compressed with bz2 (which is more compact) is needed, which 
    can be dowloaded [here](https://dumps.wikimedia.org/wikidatawiki/entities/). There is no need to 
    uncompressed the json dump.

    Note: given the limited number of entities to be imported and given that the processing of the full Wikidata
    JSON dump is time consuming, alternatively we could explore the usage of entity-level web query:
    
    https://www.wikidata.org/wiki/Special:EntityData/Q42.json
    or
    https://www.wikidata.org/w/api.php?action=wbgetentities&ids=Q24871&format=json

    batch:
    https://www.wikidata.org/w/api.php?action=wbgetentities&ids=Q775450|Q3041294|Q646968|Q434841|Q11920&format=json&props=labels

    batch and filter: 
    https://www.wikidata.org/w/api.php?action=wbgetentities&ids=Q775450|Q3041294|Q646968|Q434841|Q11920&format=json&props=labels&languages=en|de|fr

    with a cache, if we can easily get the lastrevid for comparison with the cached one
    See https://www.mediawiki.org/wiki/API:Recent_changes_stream
    and https://www.mediawiki.org/wiki/API:RecentChanges

    On the other hand, processing the wikidata full dump is not something to be done frequently. 

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
from software_kb.common.arango_common import simplify_entity

class Wikidata_harvester(Harvester):

    database_name = "wikidata"

    # list of software entities 
    software_list = []

    # list of entity identifiers corresponding to persons in relation to the entity software
    persons_list = []
    # list of properties that we consider for importing persons (P178 "developer" can also be an organization")
    # for person: P31 Q5 (instance of human) is normally enough
    person_properties = ["P50", "P170", "P178", "P767", "P3931", "P184", "P767"]

    # list of entity identifiers corresponding to software licenses in relation to the entity software
    licenses_list = []
    # list of properties that we consider for importing licenses
    licenses_properties = ["P275"]

    # list of entity identifiers corresponding to organizations in relation to the entity software
    organizations_list = []
    # list of properties that we consider for importing organizations (P178 "developer" is usually a person")
    # at some point we should have P279 (subclass) of Q43229 (organization) in a long hierarchy...
    organizations_properties = ["P8324", "P178"]

    # list of entity identifiers corresponding to publications in relation to the entity software
    publications_list = []
    # list of properties that we consider for importing publications (additional constraint: P31 instance of scholar article Q13442814)
    publications_properties = ["P1343"]

    def __init__(self, config_path="./config.yaml"):
        self.load_config(config_path)
        self.init_naming()

        # create database and collection
        if not self.sys_db.has_database(self.database_name):
            self.sys_db.create_database(self.database_name)

        self.db = self.client.db(self.database_name, username=self.config['arangodb']['arango_user'], password=self.config['arangodb']['arango_pwd'])

        if not self.db.has_collection('software'):
            self.software = self.db.create_collection('software')
        else:
            self.software = self.db.collection('software')

        if not self.db.has_collection('persons'):
            self.persons = self.db.create_collection('persons')
        else:
            self.persons = self.db.collection('persons')

        if not self.db.has_collection('licenses'):
            self.licenses = self.db.create_collection('licenses')
        else:
            self.licenses = self.db.collection('licenses')

        if not self.db.has_collection('organizations'):
            self.organizations = self.db.create_collection('organizations')
        else:
            self.organizations = self.db.collection('organizations')

        if not self.db.has_collection('publications'):
            self.publications = self.db.create_collection('publications')
        else:
            self.publications = self.db.collection('publications')

        if not self.db.has_collection('cache'):
            self.cache = self.db.create_collection('cache')
        else:
            self.cache = self.db.collection('cache')

        # list of valid entities (this is relatively small, but we might want to use a key/value store, 
        # like LMDB map, in the future)
        with open("data/resources/software.wikidata.entities", "rt") as fp:
            for line in fp:
                self.software_list.append(line.rstrip())

    def import_software_entities_and_properties(self, jsonWikidataDumpPath, reset=False):
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

                if len(line.strip().rstrip('\n')) == 0:
                    # this is usually the end
                    continue

                entityJson = None
                try:
                    entityJson = json.loads(line.rstrip(',\n'))
                except Exception as e:
                    print("Failed to parse json line at line", i, str(e))

                if not entityJson is None:    
                    if self._valid_software(entityJson):
                        entityJson = simplify_entity(entityJson)
                        # store entity in arangodb as document
                        local_id = entityJson['id']
                        if not self.software.has(local_id):
                            entityJson['_id'] = 'software/' + local_id
                            self.software.insert(entityJson)
                            self.add_extra_entities(entityJson)
        
        # write list of related entities
        self.write_extra_entity_lists()

    def _valid_software(self, jsonEntity):
        """
        Filter out json wikidata entries not relevant to software. For this we use an external
        list of entities produced by entity-fishing, which has a full KB representation for 
        exploiting hierarchy of P31 and P279 properties. Wikidata identifiers are stable. 
        """
        if jsonEntity["id"] in self.software_list:
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

    def _valid_person(self, jsonEntity):
        """
        Check that the entity is the expected list of persons and check the P31 (instance of) value
        """
        if jsonEntity["id"] in self.persons_list and "claims" in jsonEntity and "P31" in jsonEntity["claims"]:
            for value in jsonEntity["claims"]["P31"]:
                if "value" in value and value["value"] == "Q5":
                    return True
        return False 

    def _valid_license(self, jsonEntity):
        """
        Check that the entity is the expected list of license
        """
        if jsonEntity["id"] in self.licenses_list:
            return True
        else:
            return False 

    def _valid_organization(self, jsonEntity):
        """
        Check that the entity is the expected list of organization. Instead of using  P279 (subclass) of Q43229 (organization),
        which is depending on hierarchical relations, we simply that the P31 (instance of) value is available is not human (Q5).
        This approximation might need to be reconsidered!
        """
        if jsonEntity["id"] in self.organizations_list and "claims" in jsonEntity: 
            if not "P31" in jsonEntity["claims"]:
                return True
            else:
                for value in  jsonEntity["claims"]["P31"]:
                    if "value" in value and value["value"] == "Q5":
                        return False
                return True
        else:
            return False 

    def _valid_publication(self, jsonEntity):
        """
        Check that the entity is the expected list of publication and check the P31 (instance of) value for scholar work (Q13442814)
        """
        if jsonEntity["id"] in self.publications_list and "claims" in jsonEntity and "P31" in jsonEntity["claims"]:
            for value in  jsonEntity["claims"]["P31"]:
                if "value" in value and value["value"] == "Q13442814":
                    return True
        return False 

    def add_extra_entities(self, software):
        '''
        Given a software entity, we select other important related entities to be also extracted
        (persons, organization, licenses, publications)
        '''
        if "claims" in software:
            for wikidata_property, property_values in software["claims"].items():
                # persons
                if wikidata_property in self.person_properties:
                    for property_value in property_values:
                        if property_value["datatype"] == 'wikibase-item':
                            person_value = property_value["value"]
                            if not person_value in self.persons_list:
                                # note: we'll check the actual P31 entity type when loading, when we have the full record for this candidate person
                                self.persons_list.append(person_value)
                # licenses
                if wikidata_property in self.licenses_properties:
                    for property_value in property_values:
                        if property_value["datatype"] == 'wikibase-item':
                            license_value = property_value["value"]
                            if not license_value in self.licenses_list:
                                self.licenses_list.append(license_value)
                # organization
                if wikidata_property in self.organizations_properties:
                    for property_value in property_values:
                        if property_value["datatype"] == 'wikibase-item':
                            organization_value = property_value["value"]
                            if not organization_value in self.organizations_list:
                                # when loading, we will have to check the P279 chain to be sure it's an organization
                                self.organizations_list.append(organization_value)
                # publication
                if wikidata_property in self.publications_properties:
                    for property_value in property_values:
                        if property_value["datatype"] == 'wikibase-item':
                            publication_value = property_value["value"]
                            if not publication_value in self.publications_list:
                                # when loading, we will have to check the P31 as scholar article (Q13442814) for the entity
                                self.publications_list.append(publication_value)

    def write_extra_entity_lists(self):
        # person
        person_path = os.path.join("data", "resources", "persons.wikidata.entities")
        with open(person_path, "w") as person_file:
            for person in self.persons_list:
                person_file.write(person)
                person_file.write("\n")
        # license
        license_path = os.path.join("data", "resources", "licenses.wikidata.entities")
        with open(license_path, "w") as license_file:
            for license in self.licenses_list:
                license_file.write(license)
                license_file.write("\n")
        # organization
        organization_path = os.path.join("data", "resources", "organizations.wikidata.entities")
        with open(organization_path, "w") as organization_file:
            for organization in self.organizations_list:
                organization_file.write(organization)
                organization_file.write("\n")
        # publication
        publication_path = os.path.join("data", "resources", "publications.wikidata.entities")
        with open(publication_path, "w") as publication_file:
            for publication in self.publications_list:
                publication_file.write(publication)
                publication_file.write("\n")

    def load_extra_entity_list(self):
        # person
        person_path = os.path.join("data", "resources", "persons.wikidata.entities")
        if os.path.isfile(person_path):
            self.persons_list = []
            with open(person_path) as person_file:
                for line in person_file.readlines():
                    line = line.strip().rstrip('\n')
                    self.persons_list.append(line)
        # license
        license_path = os.path.join("data", "resources", "licenses.wikidata.entities")
        if os.path.isfile(license_path):
            self.licenses_list = []
            with open(license_path) as license_file:
                for line in license_file.readlines():
                    line = line.strip().rstrip('\n')
                    self.licenses_list.append(line)

        # organization
        organization_path = os.path.join("data", "resources", "organizations.wikidata.entities")
        if os.path.isfile(organization_path):
            self.organizations_list = []
            with open(organization_path) as organization_file:
                for line in organization_file.readlines():
                    line = line.strip().rstrip('\n')
                    self.organizations_list.append(line)

        # publication
        publication_path = os.path.join("data", "resources", "publications.wikidata.entities")
        if os.path.isfile(publication_path):
            self.publications_list = []
            with open(publication_path) as publication_file:
                for line in publication_file.readlines():
                    line = line.strip().rstrip('\n')
                    self.publications_list.append(line)

    def import_extra_entities(self, jsonWikidataDumpPath, reset=False):
        '''
        We make an extra pass in the Wikidata dump (slow but it should be normally done rarely)
        '''
        if reset:
            self.db.delete_collection('persons')
            self.persons = self.db.create_collection('persons')

            self.db.delete_collection('licenses')
            self.licenses = self.db.create_collection('licenses')

            self.db.delete_collection('organizations')
            self.organizations = self.db.create_collection('organizations')

            self.db.delete_collection('publications')
            self.publications = self.db.create_collection('publications')

        # load entity lists if exist
        self.load_extra_entity_list()

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
                
                if len(line.strip()) == 0:
                    # this is usually the end
                    continue

                entityJson = None
                try:
                    entityJson = json.loads(line.rstrip(',\n'))
                except Exception as e:
                    print("Failed to parse json line at line", i, str(e))
                    #print("Failed to parse json line at line", i, "json content:", line.rstrip(',\n'))

                if not entityJson is None:
                    # first rough filtering
                    if entityJson["id"] in self.persons_list or entityJson["id"] in self.licenses_list or entityJson["id"] in self.organizations_list or entityJson["id"] in self.publications_list:
                        entityJson = simplify_entity(entityJson)

                        if self._valid_person(entityJson):
                            # store entity in arangodb as document
                            local_id = entityJson['id']
                            if not self.persons.has(local_id):
                                entityJson['_id'] = 'persons/' + local_id
                                self.persons.insert(entityJson)
                        elif self._valid_license(entityJson):
                            # store entity in arangodb as document
                            local_id = entityJson['id']
                            if not self.licenses.has(local_id):
                                entityJson['_id'] = 'licenses/' + local_id
                                self.licenses.insert(entityJson)
                        elif self._valid_organization(entityJson):
                            # store entity in arangodb as document
                            local_id = entityJson['id']
                            if not self.organizations.has(local_id):
                                entityJson['_id'] = 'organizations/' + local_id
                                self.organizations.insert(entityJson)        
                        elif self._valid_publication(entityJson):
                            # store entity in arangodb as document
                            local_id = entityJson['id']
                            if not self.publications.has(local_id):
                                entityJson['_id'] = 'publications/' + local_id
                                self.publications.insert(entityJson)        

    def import_all(self, jsonWikidataDumpPath, reset=False):
        '''
        Import all relevant entities and all properties
        '''
        if reset:
            self.db.delete_collection('software')
            self.software = self.db.create_collection('software')

            self.db.delete_collection('persons')
            self.persons = self.db.create_collection('persons')

            self.db.delete_collection('licenses')
            self.licenses = self.db.create_collection('licenses')

            self.db.delete_collection('organizations')
            self.organizations = self.db.create_collection('organizations')

            self.db.delete_collection('publications')
            self.publications = self.db.create_collection('publications')


        # load non-software entity lists if exist
        self.load_extra_entity_list()

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
                
                if len(line.strip()) == 0:
                    # this is usually the end
                    continue

                entityJson = None
                try:
                    entityJson = json.loads(line.rstrip(',\n'))
                except Exception as e:
                    print("Failed to parse json line at line", i, str(e))
                    #print("Failed to parse json line at line", i, "json content:", line.rstrip(',\n'))

                if not entityJson is None:
                    # first rough filtering
                    if entityJson["id"] in self.persons_list or entityJson["id"] in self.licenses_list or entityJson["id"] in self.organizations_list or entityJson["id"] in self.publications_list:
                        entityJson = simplify_entity(entityJson)

                        if self._valid_software(entityJson):
                            # store entity in arangodb as document
                            local_id = entityJson['id']
                            if not self.software.has(local_id):
                                entityJson['_id'] = 'software/' + local_id
                                self.software.insert(entityJson)
                        elif self._valid_person(entityJson):
                            # store entity in arangodb as document
                            local_id = entityJson['id']
                            if not self.persons.has(local_id):
                                entityJson['_id'] = 'persons/' + local_id
                                self.persons.insert(entityJson)
                        elif self._valid_license(entityJson):
                            # store entity in arangodb as document
                            local_id = entityJson['id']
                            if not self.licenses.has(local_id):
                                entityJson['_id'] = 'licenses/' + local_id
                                self.licenses.insert(entityJson)
                        elif self._valid_organization(entityJson):
                            # store entity in arangodb as document
                            local_id = entityJson['id']
                            if not self.organizations.has(local_id):
                                entityJson['_id'] = 'organizations/' + local_id
                                self.organizations.insert(entityJson)        
                        elif self._valid_publication(entityJson):
                            # store entity in arangodb as document
                            local_id = entityJson['id']
                            if not self.publications.has(local_id):
                                entityJson['_id'] = 'publications/' + local_id
                                self.publications.insert(entityJson)        


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
        local_harvester = Wikidata_harvester(config_path=config_path)
        #local_harvester.import_entities(WikidataDumpPath, reset=to_reset)
        #local_harvester.import_extra_entities(WikidataDumpPath, reset=to_reset)
        local_harvester.import_all(WikidataDumpPath, reset=to_reset)
    else:
        print("No Wikidata JSON dump file path indicated")

