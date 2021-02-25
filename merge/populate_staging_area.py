'''
This script is creating the staging area to be populated by the documents imported from different sources, 
merging in practice heterogeneous schemas into a single one based on Wikidata. Entities and relations
are conflated only based on strong identifiers matching (e.g. orcid for persons, DOI for documents,
GitHub repo for software). Further non-trivial disambiguation and deduplication are done by the disambiguation
process creating the actual Knowledge Base.

The following collections of entities are created:
- software (covering software, packages/libraries, web applications)
- person
- organization
- document
- license

A graph structure is built on top of these vertex collections, with the following collection edges:
- citation (e.g. mention): as extracted from scientific literature, with a citation context (text and/or bounding 
  boxes)
- reference: a bibliographical reference which establishes a relation between entities (documents, software, ...)
- actor: for any human relationship (authorship, contributor, creator, maintainer, etc.), excluding intellectual 
  property relations
- copyrights: for any explicit copyright relationship between a creative work, creators and organization and a license
- dependencies: software dependencies
- funding: relation between a work and a funding organization

The staging area graph is then populated with method specific from the sources of imported documents, projecting 
the relevant information into the common graph, with additional data transformation if necessary:

> python3 merge/populate.py --config my_config.json

'''

import os
import sys
import json
from arango import ArangoClient
sys.path.append(os.path.abspath('./common'))
from arango_common import CommonArangoDB
import requests 
import uuid 
from pybtex.database import parse_string
from pybtex import format_from_string
import pybtex.errors
pybtex.errors.set_strict_mode(False)

class StagingArea(CommonArangoDB):

    # vertex collections 
    software = None
    persons = None
    organizations = None
    documents = None
    licenses = None

    # edge collections 
    citations = None
    references = None
    actors = None
    copyrights = None
    dependencies = None
    funding = None

    database_name = "staging"
    graph_name = "staging_graph"

    bibtex_types = ["Article", "Manual", "Unpublished", "InCollection", "Book", "Misc", "InProceedings", "TechReport", "PhdThesis", "InBook", "Proceedings", "MastersThesis"]

    def __init__(self, config_path="./config.json"):
        self.load_config(config_path)

        # create database if it doesn't exist
        if not self.sys_db.has_database(self.database_name):
            self.sys_db.create_database(self.database_name)

        self.db = self.client.db(self.database_name, username=self.config['arango_user'], password=self.config['arango_pwd'])

        if self.db.has_graph(self.graph_name):
            self.staging_graph = self.db.graph(self.graph_name)
        else:
            self.staging_graph = self.db.create_graph(self.graph_name)

        # init vertex collections if they don't exist
        if not self.staging_graph.has_vertex_collection('software'):
            self.software = self.staging_graph.create_vertex_collection('software')
        else:
            self.software = self.staging_graph.vertex_collection('software')

        if not self.staging_graph.has_vertex_collection('persons'):
            self.persons = self.staging_graph.create_vertex_collection('persons')
            # we add a hash index on the orcid identifier
            self.index_orcid = self.persons.add_hash_index(fields=['index_orcid'], unique=True, sparse=True)
        else:
            self.persons = self.staging_graph.vertex_collection('persons')

        if not self.staging_graph.has_vertex_collection('organizations'):
            self.organizations = self.staging_graph.create_vertex_collection('organizations')
        else:
            self.organizations = self.staging_graph.vertex_collection('organizations')

        if not self.staging_graph.has_vertex_collection('documents'):
            self.documents = self.staging_graph.create_vertex_collection('documents')
        else:
            self.documents = self.staging_graph.vertex_collection('documents')

        if not self.staging_graph.has_vertex_collection('licenses'):
            self.licenses = self.staging_graph.create_vertex_collection('licenses')
        else:
            self.licenses = self.staging_graph.vertex_collection('licenses')

        # init edge collections if they don't exist
        if not self.staging_graph.has_edge_collection('citations'):
            self.citations = self.staging_graph.create_edge_definition(
                edge_collection='citations',
                from_vertex_collections=['documents'],
                to_vertex_collections=['software']
            )
        else:
            self.citations = self.staging_graph.edge_collection('citations')

        if not self.staging_graph.has_edge_collection('references'):
            self.references = self.staging_graph.create_edge_definition(
                edge_collection='references',
                from_vertex_collections=['software', 'documents'],
                to_vertex_collections=['software', 'documents']
            )
        else:
            self.references = self.staging_graph.edge_collection('references')

        if not self.staging_graph.has_edge_collection('actors'):
            self.actors = self.staging_graph.create_edge_definition(
                edge_collection='actors',
                from_vertex_collections=['persons'],
                to_vertex_collections=['software', 'documents']
            )
        else:
            self.actors = self.staging_graph.edge_collection('actors')

        if not self.staging_graph.has_edge_collection('copyrights'):
            self.copyrights = self.staging_graph.create_edge_definition(
                edge_collection='copyrights',
                from_vertex_collections=['persons', 'organizations'],
                to_vertex_collections=['software']
            )
        else:
            self.copyrights = self.staging_graph.edge_collection('copyrights')

        if not self.staging_graph.has_edge_collection('dependencies'):
            self.dependencies = self.staging_graph.create_edge_definition(
                edge_collection='dependencies',
                from_vertex_collections=['software'],
                to_vertex_collections=['software']
            )
        else:
            self.dependencies = self.staging_graph.edge_collection('dependencies')

        if not self.staging_graph.has_edge_collection('funding'):
            self.funding = self.staging_graph.create_edge_definition(
                edge_collection='funding',
                from_vertex_collections=['software', "documents"],
                to_vertex_collections=['organizations']
            )
        else:
            self.funding = self.staging_graph.edge_collection('funding')


    def reset(self):
        # edge collections
        if self.staging_graph.has_edge_collection('citations'):
            self.staging_graph.delete_edge_definition('citations', purge=True)

        if self.staging_graph.has_edge_collection('references'):
            self.staging_graph.delete_edge_definition('references', purge=True)

        if self.staging_graph.has_edge_collection('actors'):
            self.staging_graph.delete_edge_definition('actors', purge=True)

        if self.staging_graph.has_edge_collection('copyrights'):
            self.staging_graph.delete_edge_definition('copyrights', purge=True)

        if self.staging_graph.has_edge_collection('dependencies'):
            self.staging_graph.delete_edge_definition('dependencies', purge=True)

        if self.staging_graph.has_edge_collection('funding'):
            self.staging_graph.delete_edge_definition('funding', purge=True)

        # vertex collections
        if self.staging_graph.has_vertex_collection('software'):
            self.staging_graph.delete_vertex_collection('software', purge=True)

        if self.staging_graph.has_vertex_collection('persons'):
            self.staging_graph.delete_vertex_collection('persons', purge=True)

        if self.staging_graph.has_vertex_collection('organizations'):
            self.staging_graph.delete_vertex_collection('organizations', purge=True)

        if self.staging_graph.has_vertex_collection('documents'):
            self.staging_graph.delete_vertex_collection('documents', purge=True)

        if self.staging_graph.has_vertex_collection('licenses'):
            self.staging_graph.delete_vertex_collection('licenses', purge=True)

        self.software = self.staging_graph.create_vertex_collection('software')
        self.persons = self.staging_graph.create_vertex_collection('persons')
        self.index_orcid = self.persons.add_hash_index(fields=['index_orcid'], unique=True, sparse=True)
        self.organizations = self.staging_graph.create_vertex_collection('organizations')
        self.documents = self.staging_graph.create_vertex_collection('documents')
        self.licenses = self.staging_graph.create_vertex_collection('licenses')

        self.citations = self.staging_graph.create_edge_definition(
                edge_collection='citations',
                from_vertex_collections=['documents'],
                to_vertex_collections=['software']
            )

        self.references = self.staging_graph.create_edge_definition(
                edge_collection='references',
                from_vertex_collections=['software', 'documents'],
                to_vertex_collections=['software', 'documents']
            )

        self.actors = self.staging_graph.create_edge_definition(
                edge_collection='actors',
                from_vertex_collections=['persons'],
                to_vertex_collections=['software', 'documents']
            )

        self.copyrights = self.staging_graph.create_edge_definition(
                edge_collection='copyrights',
                from_vertex_collections=['persons', 'organizations'],
                to_vertex_collections=['software']
            )

        self.dependencies = self.staging_graph.create_edge_definition(
                edge_collection='dependencies',
                from_vertex_collections=['software'],
                to_vertex_collections=['software']
            )

        self.funding = self.staging_graph.create_edge_definition(
                edge_collection='funding',
                from_vertex_collections=['software', "documents"],
                to_vertex_collections=['organizations']
            )

    def init_entity_from_template(self, template="software", source=None):
        '''
        Init an entity based on a template json present under resources/
        '''
        json_template = None
        template_file = os.path.join("data", "resources", template+"_template.json")
        if not os.path.isfile(template_file): 
            print("Error: template file does not exist for entity:", template)
            return None

        with open(template_file) as template_f:
            json_template_string = template_f.read()
            if not source is None:
                json_template_string = json_template_string.replace('[]', '[' + json.dumps(source) + ']')

            json_template = json.loads(json_template_string)

        return json_template


    def biblio_glutton_lookup(self, doi=None, pmcid=None, pmid=None, istex_id=None, raw_ref=None, title=None, first_author_last_name=None):
        """
        Lookup on biblio-glutton with the provided strong identifiers or the raw string and author/title information
        if available, return the full agregated biblio_glutton record
        If it's not woring, we use crossref API as fallback, with the idea of covering possible coverage gap in biblio-glutton. 
        """
        biblio_glutton_url = _biblio_glutton_url(self.config["biblio_glutton_protocol"], self.config["biblio_glutton_host"], self.config["biblio_glutton_port"])
        success = False
        jsonResult = None

        # we first call biblio-glutton with "strong" identifiers
        if doi is not None and len(doi)>0:
            response = requests.get(biblio_glutton_url, params={'doi': doi})
            success = (response.status_code == 200)
            if success:
                jsonResult = response.json()

        if not success and pmid is not None and len(pmid)>0:
            response = requests.get(biblio_glutton_url + "pmid=" + pmid)
            success = (response.status_code == 200)
            if success:
                jsonResult = response.json()     

        if not success and pmcid is not None and len(pmcid)>0:
            response = requests.get(biblio_glutton_url + "pmc=" + pmcid)  
            success = (response.status_code == 200)
            if success:
                jsonResult = response.json()

        if not success and istex_id is not None and len(istex_id)>0:
            response = requests.get(biblio_glutton_url + "istexid=" + istex_id)
            success = (response.status_code == 200)
            if success:
                jsonResult = response.json()
        
        if not success and doi is not None and len(doi)>0:
            # let's call crossref as fallback for the X-months gap
            # https://api.crossref.org/works/10.1037/0003-066X.59.1.29
            user_agent = {'User-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:68.0) Gecko/20100101 Firefox/68.0 (mailto:' 
                + self.config['crossref_email'] + ')'} 
            response = requests.get(self.config['crossref_base']+"/works/"+doi, headers=user_agent)
            if response.status_code == 200:
                jsonResult = response.json()['message']
            else:
                success = False
                jsonResult = None

        if not success and first_author_last_name!= None and title != None:
            if raw_ref != None:
                # call to biblio-glutton with combined raw ref, title and last author first name
                params = {"biblio": raw_ref, "atitle": title, "firstAuthor": first_author_last_name}
                response = requests.get(biblio_glutton_url, params=params)
                success = (response.status_code == 200)
                if success:
                    jsonResult = response.json()
            else:
                # call to biblio-glutton with only title and last author first name
                params = {"atitle": title, "firstAuthor": first_author_last_name}
                response = requests.get(biblio_glutton_url, params=params)
                success = (response.status_code == 200)
                if success:
                    jsonResult = response.json()

        if not success and raw_ref != None:
            # call to biblio-glutton with only raw ref
            params = {"biblio": raw_ref, "postValidate": "true"}
            response = requests.get(biblio_glutton_url, data=params)  
            success = (response.status_code == 200)
            if success:
                jsonResult = response.json()

        '''
        if not success and raw_ref != None:
            # fallback for raw reference with CrossRef
            user_agent = {'User-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:68.0) Gecko/20100101 Firefox/68.0 (mailto:' 
                + self.config['crossref_email'] + ')'} 
            params = { "query.bibliographic": raw_ref }
            response = requests.get(self.config['crossref_base']+"/works/", params=params, headers=user_agent)
            if response.status_code == 200:
                jsonResult = response.json()['message']
            else:
                success = False
                jsonResult = None
        '''

        # filter out references if present
        if jsonResult != None:
            if "reference" in jsonResult:
                del jsonResult["reference"]

        return jsonResult

    def unpaywalling_doi(self, doi):
        """
        Check the Open Access availability of the DOI via Unpaywall, return the best download URL or None otherwise.
        We need to use the Unpaywall API to get fresh information, because biblio-glutton is based on the 
        Unpaywall dataset dump which has a 7-months gap.
        """
        response = requests.get(self.config["unpaywall_base"] + doi, params={'email': self.config["unpaywall_email"]}).json()
        if response['best_oa_location'] and response['best_oa_location']['url_for_pdf']:
            return response['best_oa_location']['url_for_pdf']
        elif response['best_oa_location']['url'].startswith(self.config['pmc_base_web']):
            return response['best_oa_location']['url']+"/pdf/"
        # we have a look at the other "oa_locations", which might have a `url_for_pdf` ('best_oa_location' has not always a 
        # `url_for_pdf`, for example for Elsevier OA articles)
        for other_oa_location in response['oa_locations']:
            # for a PMC file, we can concatenate /pdf/ to the base, eg https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7029158/pdf/
            # but the downloader will have to use a good User-Agent and follow redirection
            if other_oa_location['url'].startswith(self.config['pmc_base_web']):
                return other_oa_location['url']+"/pdf/"
            if other_oa_location['url_for_pdf']:
                return other_oa_location['url_for_pdf']
        return None

    def process_reference_block(self, references_block, entity, source_ref):
        '''
        Process the raw and bibtex references in a reference json list to create fully parsed 
        representations with DOI/PMID/PMCID resolution
        '''
        has_bibtex = False
        # if we have bibtex entries
        for reference in references_block:
            if "bibtex" in reference:
                has_bibtex = True
                break

        # signature for the processed strings, to avoid processing duplicated entries
        signatures = []

        for reference in references_block:
            glutton_biblio = None

            if "bibtex" in reference:
                bibtex_str = reference["bibtex"]
                local_signature =  ''.join(e for e in bibtex_str if e.isalnum())
                if local_signature in signatures:
                    # already processed
                    continue
                else:
                    signatures.append(local_signature)

                # force a key if not present, for having valid parsing
                for bibtext_type in self.bibtex_types:
                    bibtex_str = bibtex_str.replace("@"+bibtext_type+"{,", "@"+bibtext_type+"{toto,")

                biblio = None
                try:
                    biblio = parse_string(bibtex_str, "bibtex")
                except:
                    print("Failed to parse the bibtext string:", bibtex_str)

                if biblio != None:
                    for key in biblio.entries:
                        local_title = None
                        if "title" in biblio.entries[key].fields:
                            local_title = biblio.entries[key].fields["title"]
                        first_author_last_name = None
                        local_authors = biblio.entries[key].persons
                        if local_authors is not None and "author" in local_authors:
                            all_authors = local_authors["author"]
                            if len(all_authors) > 0 and len(all_authors[0].last_names) > 0:
                                first_author_last_name = all_authors[0].last_names[0]
                        text_format_ref = None
                        try:
                            text_format_ref = format_from_string(bibtex_str, style="plain")
                        except:
                            print("Failed to serialize the bibtext entry:", bibtex_str)

                        if text_format_ref == None:
                            continue
                            
                        res_format_ref = ""
                        for line_format_ref in text_format_ref.split("\n"):
                            if line_format_ref.startswith("\\newblock"):
                                res_format_ref += line_format_ref.replace("\\newblock", "")
                            elif len(line_format_ref.strip()) != 0 and not line_format_ref.startswith("\\"):
                                res_format_ref += line_format_ref

                        res_format_ref = res_format_ref.strip()
                        res_format_ref = res_format_ref.replace("\\emph{", "")
                        res_format_ref = res_format_ref.replace("\\url{", "")
                        res_format_ref = res_format_ref.replace("}", "")

                        # we can call biblio-glutton with the available information
                        glutton_biblio = self.biblio_glutton_lookup(raw_ref=res_format_ref, title=local_title, first_author_last_name=first_author_last_name)

            if "raw" in reference and glutton_biblio == None and not has_bibtex:
                # this can be sent to biblio-glutton
                res_format_ref = reference["raw"]
                local_signature =  ''.join(e for e in res_format_ref if e.isalnum())
                if local_signature in signatures:
                    # already processed
                    continue
                else:
                    signatures.append(local_signature)

                glutton_biblio = stagingArea.biblio_glutton_lookup(raw_ref=reference["raw"])

            if glutton_biblio != None:
                # we can create a document entry for the referenced document, 
                # and a reference relation between the given entity and this document
                local_id = self.get_uid()
                local_doc = self.init_entity_from_template("document", source=source_ref)
                if local_doc is None:
                    raise("cannot init document entity from default template")

                local_doc['_key'] = local_id
                local_doc['_id'] = "documents/" + local_id

                # document metadata stays as they are (e.g. full CrossRef record)
                local_doc['metadata'] = glutton_biblio

                if not self.staging_graph.has_vertex(local_doc["_id"]):
                    self.staging_graph.insert_vertex("documents", local_doc)

                relation = {}
                relation["claims"] = {}
                # "P2860" property "cites work "
                relation["claims"]["P2860"] = []
                local_value = {}
                local_value["references"] = []
                local_value["references"].append(source_ref)
                relation["claims"]["P2860"].append(local_value)

                relation["_from"] = entity['_id']
                relation["_to"] = local_doc['_id']

                relation["_key"] = entity["_key"] + "_" + local_doc['_key']
                relation["_id"] = "references/" + relation["_key"]
                if not self.staging_graph.has_edge(relation["_id"]):
                    self.staging_graph.insert_edge("references", edge=relation)

    def get_uid(self):
        local_id = uuid.uuid4().hex
        local_id = local_id.replace("-", "")
        local_id = local_id[:-24]
        return local_id

def _biblio_glutton_url(biblio_glutton_protocol, biblio_glutton_host, biblio_glutton_port):
    biblio_glutton_base = biblio_glutton_protocol + "://" + biblio_glutton_host
    if biblio_glutton_base.endswith("/"):
        res = biblio_glutton_base[:-1]
    else: 
        res = biblio_glutton_base
    if biblio_glutton_port is not None and len(biblio_glutton_port)>0:
        res += ":"+biblio_glutton_port
    return res+"/service/lookup?"

def _grobid_url(grobid_protocol, grobid_url, grobid_port):
    the_url = grobid_protocol + "://" + grobid_base
    if the_url.endswith("/"):
        the_url = the_url[:-1]
    if grobid_port is not None and len(grobid_port)>0:
        the_url += ":"+grobid_port
    the_url += "/api/"
    return the_url

