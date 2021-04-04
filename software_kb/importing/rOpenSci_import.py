'''
    Access, convert and load rOpenSci universe package metadata in the Knowledge Base

    See API at https://ropensci.r-universe.dev/
'''

import requests
import argparse
import json
from harvester import Harvester
from arango import ArangoClient
import re
from import_common import process_r_author_field, clean_field, process_author_field, process_url_field, is_git_repo, process_boolean_field, process_maintainer_field
from collections import OrderedDict

base_url = "https://ropensci.r-universe.dev/"
packages_path = "packages/"
maintainer_path = "maintainers/"
descriptions_path = "descriptions/"

# the following list of fields are considered to be only related to particular build and could be ignored 
skipped_fields = ['Packaged', 'VignetteBuilder', '_type', '_file', 'MD5sum', '_builder', '_user', 'Built', 'Encoding', 'LazyData', 'RoxygenNote', 'Remotes', 'Collate']

class rOpenSci_harvester(Harvester):

    database_name = "rOpenSci"

    def __init__(self, config_path="./config.yaml"):
        self.load_config(config_path)

        # create database and collection
        if not self.sys_db.has_database(self.database_name):
            self.sys_db.create_database(self.database_name)

        self.db = self.client.db(self.database_name, username=self.config['arangodb']['arango_user'], password=self.config['arangodb']['arango_pwd'])

        if not self.db.has_collection('packages'):
            self.packages = self.db.create_collection('packages')
        else:
            self.packages = self.db.collection('packages')

        if not self.db.has_collection('cache'):
            self.cache = self.db.create_collection('cache')
        else:
            self.cache = self.db.collection('cache')


    def import_packages(self, reset=False):
        if reset:
            self.db.delete_collection('packages')
            self.packages = self.db.create_collection('packages')

        # get the list of packages
        jsonResult = None
        packages_url = base_url + packages_path
        local_path = self.access_file(packages_url, use_cache=False)
        if local_path is not None:
            # get the content from file
            with open(local_path) as file:
                jsonResult = json.load(file)
        else:
            print("Fail to retrieve the list of packages", packages_url, "status", response.status_code)

        if jsonResult == None:
            return

        for package in jsonResult:
            # get the list of versions for this package
            jsonResultVersions = None
            packages_versions_url = base_url + packages_path + package
            local_path = self.access_file(packages_versions_url, use_cache=False)
            if local_path is not None:
                # get the content from file
                with open(local_path) as file:
                    jsonResultVersions = json.load(file)
            else:
                print("Fail to retrieve the list of package versions", packages_versions_url)

            if jsonResultVersions == None:
                continue

            # sort by version number, descending
            jsonResultVersions.sort(reverse=True)

            for packageVersion in jsonResultVersions:
                # finally get the package version
                package_version_url = packages_versions_url + "/" + packageVersion
                jsonResultVersionPackage = None
                local_path = self.access_file(package_version_url)
                if local_path is not None:
                    # get the content from file
                    with open(local_path) as file:
                        jsonResultVersionPackage = json.load(file)
                else:
                    print("Fail to retrieve the list of package with version", package_version_url)

                if jsonResultVersionPackage == None:
                    continue

                package_json = self.convert_package_json(jsonResultVersionPackage)
                if package_json is None:
                    continue
                # insert json document
                package_json['_id'] = 'packages/' + package_json['_id']
                if not self.packages.has(package_json['_id']):
                    # for safety, check uniqueness of package name too (latestversion of each package comes first)
                    cursor = self.packages.find({'Package': package_json["Package"]}, skip=0, limit=1)
                    if cursor.count() == 0:
                        self.packages.insert(package_json)
                        # we only import the full record for the latest version
                        break

    '''
    not used, we get it via the normal package input
    '''
    def import_maintainers(self, reset=False):
        if reset:
            self.db.delete_collection('maintainers')
            self.maintainers = self.db.create_collection('maintainers')
            
        jsonResult = None
        response = requests.get(base_url + maintainer_path)
        if success:
            jsonResult = response.json()
        else:
            print("Fail to retrieve the list of maintainers", base_url + maintainer_path, "status", response.status_code)

        for maintainer in jsonResult:
            print(json.dumps(maintainer))
            maintainer_json = self.convert_maintainer_json(package_json)
            # insert json document
            self.maintainers.insert_document(maintainer_json)

    '''
    not used, we get it via the normal package input
    '''
    def import_package_descriptions(self):
        jsonResult = None
        response = requests.get(base_url + descriptions_path)
        if success:
            jsonResult = response.json()
        else:
            print("Fail to retrieve the list of package descriptions", base_url + descriptions_path, "status", response.status_code)

    def convert_package_json(self, package_json):
        if package_json is None or len(package_json) == 0:
            return None

        package_json = package_json[0]

        if "Description" in package_json:
            package_json["Description"] = clean_field(package_json["Description"])

        # the field Authors@R is not JSON, we need a custom parse
        if not 'Authors@R' in package_json:
            print("no Authors@R field for", package_json["Package"])
            # in this case the author field, also parsed, will be the fqall back
            return package_json

        author_field = package_json['Authors@R']
        persons = process_r_author_field(author_field)
        if len(persons) > 0:
            #print(persons)
            package_json['Authors@R'] = persons

        if "Author" in package_json:
            package_json['Author'] = process_author_field(package_json['Author'])

        if "Title" in package_json:
            package_json['Title'] = clean_field(package_json["Title"])

        # _published field is related to the latest updated publication of the package, which we clarify
        if '_published' in package_json:
            package_json['latest_published'] = package_json['_published']
            del package_json['_published']

        # field URL is usually a raw list, than we can convert into a json list
        if 'URL' in package_json:
            package_json['URL'] = process_url_field(package_json['URL'])

            # in case we have one git repo in the list of URL, we can seprate it from the from other url
            # in case we have a URL to a manual/doc, we can use the manual field as for CRAN
            to_be_removed = []
            for url in package_json['URL']:
                if is_git_repo(url):
                    to_be_removed.append(url)
                    if url.startswith("http://"):
                        url = url.replace("http://", "https://")
                    package_json['git_repository'] = url
                    continue
                if url.startswith("https://docs.ropensci.org"):
                    package_json['Manual'] = url
                    to_be_removed.append(url)
                    continue
            if to_be_removed != None:
                for one_to_be_removed in to_be_removed:
                    package_json['URL'].remove(one_to_be_removed)

        if "NeedsCompilation" in package_json:
            package_json["NeedsCompilation"] = process_boolean_field(package_json["NeedsCompilation"])

        if "Maintainer" in package_json:
            package_json["Maintainer"] = process_maintainer_field(package_json["Maintainer"])

        for field in skipped_fields:
            if field in package_json:
                del package_json[field]

        # we can infer the a github repo if missing from the bug report url 
        if 'git_repository' not in package_json and 'BugReports' in package_json:
            if is_git_repo(package_json['BugReports']):
                if package_json['BugReports'].endswith("/issues/"):
                    package_json['git_repository'] = package_json['BugReports'].replace("issues/", "")

        return package_json

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Harvest and update rOpenSci public data")
    parser.add_argument("--config", default="./config.yaml", help="path to the config file, default is ./config.yaml") 
    parser.add_argument("--reset", action="store_true", help="reset existing collections and re-import all rOpenSci records") 

    args = parser.parse_args()
    config_path = args.config
    to_reset = args.reset

    local_harvester = rOpenSci_harvester(config_path=config_path)
    local_harvester.import_packages(reset=to_reset)
