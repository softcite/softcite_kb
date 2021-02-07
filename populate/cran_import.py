'''
    Access, convert and load CRAN package metadata in the Knowledge Base

    We harvest cran.r-project.org 
'''

import requests
import argparse
import json
import re
from harvester import Harvester
from arango import ArangoClient
from bs4 import BeautifulSoup
from common import process_author_field, clean_field, process_url_field, process_maintainer_field, process_boolean_field, process_dependency_field

base_url = 'http://crandb.r-pkg.org/'
# example package metadata: http://crandb.r-pkg.org/knitr

package_list_crandb = 'http://crandb.r-pkg.org/-/desc'
package_list_cran_raw = 'https://cran.r-project.org/src/contrib/PACKAGES'
# raw package: https://cran.r-project.org/package=knitr
# citation raw information: "https://cran.r-project.org/web/packages/%s/citation.html"

class cran_harvester(Harvester):

    database_name = "CRAN"

    def __init__(self, config_path="./config.json"):
        self.load_config(config_path)

        # create database and collection
        if not self.sys_db.has_database(self.database_name):
            self.sys_db.create_database(self.database_name)

        self.db = self.client.db(self.database_name, username=self.config['arango_user'], password=self.config['arango_pwd'])

        if not self.db.has_collection('packages'):
            self.packages = self.db.create_collection('packages')
        else:
            self.packages = self.db.collection('packages')

        if not self.db.has_collection('cache'):
            self.packages = self.db.create_collection('cache')
        else:
            self.packages = self.db.collection('cache')

        if not self.db.has_collection('cache'):
            self.cache = self.db.create_collection('cache')
        else:
            self.cache = self.db.collection('cache')


    def import_packages(self, reset=False):
        if reset:
            self.db.delete_collection('packages')
            self.packages = self.db.create_collection('packages')

        all_packages = []

        # get the list of packages
        local_path = self.access_file(package_list_cran_raw, use_cache=False)
        textResult = None
        if local_path is not None:
            # get the content from file
            with open(local_path) as file:
                textResult = file.read()
        else:
            print("Fail to retrieve the list of packages", packages_url, "status", response.status_code)
            return

        textResultPackages = textResult.split("\n\n")
        for textResultPackage in textResultPackages:        
            json_package = _convert_raw_package_summary(textResultPackage)
            all_packages.append(json_package)

        print("total of available packages:", len(all_packages))

        for one_package in all_packages:
            # get full raw package record
            # https://cran.r-project.org/package=knitr
            local_url = one_package["Package"]
            local_path = self.access_file(local_url)
            if local_path is not None:
                # get the content from file
                content_html = None
                with open(local_path) as file:
                    content_html = file.read()
                json_package = _convert_raw_package_record(content_html, one_package)

                print(json.dumps(json_package))

    def set_num_downloads(self):
        '''
        From depsy/models/cran_package.py 
        '''
        self.num_downloads = 0

        url_template = "http://cranlogs.r-pkg.org/downloads/daily/1900-01-01:2020-01-01/%s"
        data_url = url_template % self.project_name
        print(data_url)
        response = requests.get(data_url)
        if "day" in response.text:
            data = {}
            all_days = response.json()[0]["downloads"]
            for download_dict in all_days:
                self.num_downloads += download_dict["downloads"]
        print(u"setting num_downloads to {}".format(self.num_downloads))


def _convert_raw_package_summary(textResultPackage):
    ''' 
    Convert raw package input into json, e.g. 
        Package: A3
        Version: 1.0.0
        Depends: R (>= 2.15.0), xtable, pbapply
        Suggests: randomForest, e1071
        License: GPL (>= 2)
        MD5sum: 027ebdd8affce8f0effaecfcd5f5ade2
        NeedsCompilation: no
    '''
    lines = textResultPackage.split("/n")
    package = {}
    package['Package'] = _val_line(lines[0])
    package['Version'] = _val_line(lines[1])
    # note: the rest will be extracted from the full package record
    return package

def _convert_raw_package_record(packageRecordHtml, json_package):
    orcid_pattern = r'([0-9]{4}\-[0-9]{4}\-[0-9]{4}\-[0-9]{4})'
    regex_orcid = re.compile(orcid_pattern)

    soup = BeautifulSoup(packageRecordHtml, "lxml")
    json_package['Title'] = clean_field(soup.body.h2.text)

    # package name is prefixed in the title, we can strip it
    if 'Package' in json_package:
        if json_package['Title'].startswith(json_package['Package']):
            json_package['Title'] = json_package['Title'][len(json_package['Package'])+1:].strip()

    json_package['Description'] = clean_field(soup.body.p.text)
    
    # the rest is via a 2-column tables encoding basically attribute/value
    tables = soup.findAll("table")

    table1 = None
    for table in tables:
        if table.has_attr('summary'):
            # first one is the package metadata summary
            table1 = table
            break

    if table1 is not None:
        rows = table1.find("tbody").find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) != 2:
                continue
            field = cells[0].get_text()
            print(field)
            if field == "Version:":
                json_package["Version"] = clean_field(cells[1].get_text())
            elif field == "Maintainer:":
                json_package["Maintainer"] = process_maintainer_field(clean_field(cells[1].get_text()))
            elif field == "Author:":
                json_package["Authors"] = process_author_field(clean_field(cells[1].get_text()))
            elif field == "License:":
                json_package["License"] = clean_field(cells[1].get_text())
            elif field == "Published:":
                json_package["latest_published"] = clean_field(cells[1].get_text())
            elif field == "BugReports:":
                urls = process_url_field(cells[1].get_text())
                if len(urls) > 0:
                    json_package["BugReports"] = urls[0]
            elif field == "NeedsCompilation:":
                json_package["NeedsCompilation"] = process_boolean_field(cells[1].get_text())
            elif field == "URL:":
                json_package["URL"] = process_url_field(cells[1].get_text())
            elif field == "Depends:":
                if "_hard_deps" in json_package:
                    json_package["_hard_deps"] = json_package["_hard_deps"] + process_dependency_field(cells[1].get_text(), "Depends")
                else:
                    json_package["_hard_deps"] = process_dependency_field(cells[1].get_text(), "Depends")
            elif field == "Imports:":
                if "_hard_deps" in json_package:
                    json_package["_hard_deps"] = json_package["_hard_deps"] + process_dependency_field(cells[1].get_text(), "Imports")
                else:
                    json_package["_hard_deps"] = process_dependency_field(cells[1].get_text(), "Imports")
            elif field == "Suggests:":
                json_package["_soft_deps"] = process_dependency_field(cells[1].get_text(), "Suggest")

            #print(cells[1].get_text())

    table2 = None
    rank = 0
    for table in tables:
        if table.has_attr('summary'):
            rank += 1
            if rank == 2:
                # second one is the download summary 
                table2 = table
                break
    if table2 is not None:
        rows = table2.find("tbody").find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) != 2:
                continue
            field = cells[0].get_text().strip()
            print(field)

            if field == 'Reference manual:':
                if cells[1].find("a") != None:
                    json_package["Manual"] = cells[1].find("a")['href']

    table3 = None
    rank = 0
    for table in tables:
        if table.has_attr('summary'):
            rank += 1
            if rank == 3:
                # third one is the reverse dependency summary 
                table3 = table
    if table3 is not None:
        rows = table3.find("tbody").find_all("tr")

        for row in rows:
            cells = row.find_all("td")
            if len(cells) != 2:
                continue
            field = cells[0].get_text()
            print(field)

            #"Reverse depends:"
            #"Reverse imports:"
            #"Reverse suggests:"
            #"Reverse enhances:"

    return json_package

def _val_line(line):
    ind = line.find(":")
    if ind != -1:
        return line[ind:].strip()
    else: 
        return None

    