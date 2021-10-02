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

> python3 merging/populate.py --config my_config.yaml

'''

import os
import sys
import json
from arango import ArangoClient
from software_kb.common.arango_common import CommonArangoDB
import requests 
import uuid 
import hashlib
from pybtex.database import parse_string
from pybtex import format_from_string
import pybtex.errors
pybtex.errors.set_strict_mode(False)
from lxml import etree 
import logging
import logging.handlers

logging.getLogger("pybtex").propagate = False

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

    def __init__(self, config_path="./config.yaml"):
        self.load_config(config_path)

        # create database if it doesn't exist
        if not self.sys_db.has_database(self.database_name):
            self.sys_db.create_database(self.database_name)

        self.db = self.client.db(self.database_name, username=self.config['arangodb']['arango_user'], password=self.config['arangodb']['arango_pwd'])

        if not self.db.has_collection('cache'):
            self.cache = self.db.create_collection('cache')
        else:
            self.cache = self.db.collection('cache')

        if self.db.has_graph(self.graph_name):
            self.staging_graph = self.db.graph(self.graph_name)
        else:
            self.staging_graph = self.db.create_graph(self.graph_name)

        # init vertex collections if they don't exist
        if not self.staging_graph.has_vertex_collection('software'):
            self.software = self.staging_graph.create_vertex_collection('software')
            self.index_software_names = self.software.add_hash_index(fields=['labels', 'aliases[*]'], unique=False, sparse=False)
            self.index_entity = self.software.add_hash_index(fields=['index_entity'], unique=False, sparse=True)
        else:
            self.software = self.staging_graph.vertex_collection('software')

        if not self.staging_graph.has_vertex_collection('persons'):
            self.persons = self.staging_graph.create_vertex_collection('persons')
            # we add a hash index on the orcid identifier
            self.index_orcid = self.persons.add_hash_index(fields=['index_orcid'], unique=True, sparse=True)
            # we add a hash index on the full name 
            self.index_full_name = self.persons.add_hash_index(fields=['labels'], unique=False, sparse=False)
            # add a hash index on first letter forname+last name
            self.index_name_key = self.persons.add_hash_index(fields=['index_name_key'], unique=False, sparse=True)
        else:
            self.persons = self.staging_graph.vertex_collection('persons')

        if not self.staging_graph.has_vertex_collection('organizations'):
            self.organizations = self.staging_graph.create_vertex_collection('organizations')
            self.index_organization_names = self.organizations.add_hash_index(fields=['labels', 'aliases[*]'], unique=False, sparse=False)
        else:
            self.organizations = self.staging_graph.vertex_collection('organizations')

        if not self.staging_graph.has_vertex_collection('documents'):
            self.documents = self.staging_graph.create_vertex_collection('documents')
            # we add a hash index on the DOI identifier (note DOI is not case-sensitive, so we lowercase 
            # everything and look-up must be made with lower case DOI too)
            self.index_doi = self.documents.add_hash_index(fields=['index_doi'], unique=False, sparse=True)
            # we add an index on a title+first author last name signature
            self.index_title_author = self.documents.add_hash_index(fields=['index_title_author'], unique=False, sparse=True)
        else:
            self.documents = self.staging_graph.vertex_collection('documents')

        if not self.staging_graph.has_vertex_collection('licenses'):
            self.licenses = self.staging_graph.create_vertex_collection('licenses')
            self.index_licences_names = self.licenses.add_hash_index(fields=['labels', 'aliases[*]'], unique=False, sparse=False)
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

        self.init_merging_collections()

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
        self.index_software_names = self.software.add_hash_index(fields=['labels', 'aliases[*]'], unique=False, sparse=False)
        self.index_entity = self.software.add_hash_index(fields=['index_entity'], unique=False, sparse=True)

        self.persons = self.staging_graph.create_vertex_collection('persons')
        self.index_orcid = self.persons.add_hash_index(fields=['index_orcid'], unique=True, sparse=True)
        self.index_full_name = self.persons.add_hash_index(fields=['labels'], unique=False, sparse=False)
        self.index_name_key = self.persons.add_hash_index(fields=['index_name_key'], unique=False, sparse=True)
        
        self.organizations = self.staging_graph.create_vertex_collection('organizations')
        self.index_organization_names = self.organizations.add_hash_index(fields=['labels', 'aliases[*]'], unique=False, sparse=False)
        
        self.documents = self.staging_graph.create_vertex_collection('documents')
        self.index_doi = self.documents.add_hash_index(fields=['index_doi'], unique=False, sparse=True)
        self.index_title_author = self.documents.add_hash_index(fields=['index_title_author'], unique=False, sparse=True)

        self.licenses = self.staging_graph.create_vertex_collection('licenses')
        self.index_licences_names = self.licenses.add_hash_index(fields=['labels', 'aliases[*]'], unique=False, sparse=False)

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

        self.reset_merging_collections()

    def init_merging_collections(self):
        '''
        Create collections to keep track of merging decisions for the different entities (vertex only). 
        '''

        # keep track of list of entities to be merged (first entity of the list will be the host of the merging)
        if not self.staging_graph.has_vertex_collection('merging_lists'):
            self.merging_lists = self.staging_graph.create_vertex_collection('merging_lists')
        else:
            self.merging_lists = self.staging_graph.vertex_collection('merging_lists')

        # keep track for a given entity of the list of entities where is should be merged     
        if not self.staging_graph.has_vertex_collection('merging_entities'):
            self.merging_entities = self.staging_graph.create_vertex_collection('merging_entities')
        else:
            self.merging_entities = self.staging_graph.vertex_collection('merging_entities')

    def reset_merging_collections(self):
        '''
        Reinit the collections to keep track of merging decisions for the different entities (vertex only). 
        '''
        if self.staging_graph.has_vertex_collection('merging_lists'):
            self.staging_graph.delete_vertex_collection('merging_lists', purge=True)

        if self.staging_graph.has_vertex_collection('merging_entities'):
            self.staging_graph.delete_vertex_collection('merging_entities', purge=True)

        self.merging_list = self.staging_graph.create_vertex_collection('merging_lists')
        self.merging_entities = self.staging_graph.create_vertex_collection('merging_entities')

    def init_entity_from_template(self, template="software", source=None):
        '''
        Init an entity based on a template json present under resources/
        '''
        json_template = None
        template_file = os.path.join("data", "resources", template+"_template.json")
        if not os.path.isfile(template_file): 
            logging.error("Error: template file does not exist for entity: " + template)
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

        The query and result are not cached. 
        """
        biblio_glutton_url = _biblio_glutton_url(self.config['biblio-glutton']["biblio_glutton_protocol"], self.config['biblio-glutton']["biblio_glutton_host"], self.config['biblio-glutton']["biblio_glutton_port"])
        success = False
        jsonResult = None

        # we first call biblio-glutton with "strong" identifiers
        if doi is not None and len(doi)>0:
            the_result, success, _ = self.access_web_api_get(biblio_glutton_url, params={'doi': doi})
            if success:
                jsonResult = the_result

        if not success and pmid is not None and len(pmid)>0:
            the_result, success, _ = self.access_web_api_get(biblio_glutton_url, params={'pmid': pmid})
            if success:
                jsonResult = the_result  

        if not success and pmcid is not None and len(pmcid)>0:
            the_result, success, _ = self.access_web_api_get(biblio_glutton_url, params={'pmc': pmcid})
            if success:
                jsonResult = the_result

        if not success and istex_id is not None and len(istex_id)>0:
            the_result, success, _ = self.access_web_api_get(biblio_glutton_url, params={'istexid': istex_id})
            if success:
                jsonResult = the_result
        
        if not success and doi is not None and len(doi)>0:
            # let's call crossref as fallback for the X-months gap
            # https://api.crossref.org/works/10.1037/0003-066X.59.1.29
            user_agent = {'User-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:68.0) Gecko/20100101 Firefox/68.0 (mailto:' 
                + self.config['crossref']['crossref_email'] + ')'} 
            the_result, success, _ = self.access_web_api_get(self.config['crossref']['crossref_base']+"/works/"+doi, headers=user_agent)
            if success:
                jsonResult = the_result['message']

        if not success and first_author_last_name != None and title != None:
            if raw_ref != None:
                # call to biblio-glutton with combined raw ref, title and last author first name
                params = {"biblio": raw_ref, "atitle": title, "firstAuthor": first_author_last_name}
                the_result, success, _ = self.access_web_api_get(biblio_glutton_url, params=params)
                if success:
                    jsonResult = the_result
            else:
                # call to biblio-glutton with only title and last author first name
                params = {"atitle": title, "firstAuthor": first_author_last_name}
                the_result, success, _ = self.access_web_api_get(biblio_glutton_url, params=params)
                if success:
                    jsonResult = the_result

        if not success and raw_ref != None:
            # call to biblio-glutton with only raw ref
            params = {"biblio": raw_ref, "postValidate": "true"}
            the_result, success, _ = self.access_web_api_get(biblio_glutton_url, data=params)
            if success:
                jsonResult = the_result

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
        params = {'email': self.config['unpaywall']["unpaywall_email"]}
        response, success, _ = self.access_web_api_get(self.config['unpaywall']["unpaywall_base"] + doi, data=params)
        if success:
            if response['best_oa_location'] and response['best_oa_location']['url_for_pdf']:
                return response['best_oa_location']['url_for_pdf']
            elif response['best_oa_location']['url'].startswith(self.config['unpaywall']['pmc_base_web']):
                return response['best_oa_location']['url']+"/pdf/"
            # we have a look at the other "oa_locations", which might have a `url_for_pdf` ('best_oa_location' has not always a 
            # `url_for_pdf`, for example for Elsevier OA articles)
            for other_oa_location in response['oa_locations']:
                # for a PMC file, we can concatenate /pdf/ to the base, eg https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7029158/pdf/
                # but the downloader will have to use a good User-Agent and follow redirection
                if other_oa_location['url'].startswith(self.config['unpaywall']['pmc_base_web']):
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
                    logging.warning("Failed to parse the bibtext string: " + bibtex_str)

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
                            logging.warning("Failed to serialize the bibtext entry: " + bibtex_str)

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

                # doi index
                if "DOI" in glutton_biblio:
                    local_doc["index_doi"] = glutton_biblio["DOI"].lower()

                # title/first author last name index
                if "title" in glutton_biblio and 'author' in glutton_biblio:
                    local_key = self.title_author_key(glutton_biblio["title"], glutton_biblio['author'])
                    if local_key != None:
                        local_doc["index_title_author"] = local_key
                                

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
        local_id = local_id[:-8]
        return local_id

    def access_web_api_get(self, url, params=None, data=None, headers=None, use_cache=True, json_content=True):
        '''
        This is a simple GET cached call to a given web service, with response content as JSON or text only
        '''
        response_data = None
        response_doc = None
        final_key = None

        if use_cache:
            # check if cached
            local_key = url
            if params != None:
                for param_key, param_value in params.items():
                    local_key += "_" + param_key + "_" + param_value
            if data != None:
                for param_key, param_value in data.items():
                    local_key += "_" + param_key + "_" + param_value

            hash_object = hashlib.md5(local_key.encode())
            final_key = hash_object.hexdigest()

            response_doc = self.cache.get({'_key': final_key})

        if response_doc is None:
            # not cached, web access
            if params != None and len(params) > 0:
                response = requests.get(url, params=params, headers=headers)
            elif data != None and len(data) > 0:
                response = requests.get(url, data=data, headers=headers)
            else:
                response = requests.get(url, headers=headers)

            status = response.status_code
            success = (status == 200)
            if success and json_content:
                response_data = response.json()
            elif success:
                response_data = response.text

            if use_cache and final_key != None:
                # cache the result for next time
                local_doc = {}
                local_doc["data"] = response_data
                local_doc["success"] = success
                local_doc["status"] = status
                local_doc["_key"] = final_key
                local_doc["_id"] = "cache/" + final_key
                self.cache.insert(local_doc)
        else:
            success = response_doc["success"]
            status = response_doc["status"]
            response_data = response_doc["data"]

        return response_data, success, status

    def tei2json(self, tei):
        '''
        Transform a bibliographical reference in TEI into JSON, similar to CrossRef JSON format (but simplified)
        '''
        json_bib = {}
        root = etree.fromstring(tei)

        # xpaths
        x_title = '/biblStruct/analytic/title[@level="a"]'
        x_doi = '/biblStruct/analytic/idno[@type="DOI"]' 
        x_pmid = '/biblStruct/analytic/idno[@type="PMID"]'
        x_pmcid = '/biblStruct/analytic/idno[@type="PMCID"]'
        x_oa_link = '/biblStruct/analytic/ptr[@type="open-access"]/@target'

        x_publisher = '/biblStruct/monogr/imprint/publisher'
        x_journal = '/biblStruct/monogr/title[@level="j"]'
        x_monograph = '/biblStruct/monogr/title[@level="m"]'

        x_volume = '/biblStruct/monogr/imprint/biblScope[@unit="volume"]'
        x_issue = '/biblStruct/monogr/imprint/biblScope[@unit="issue"]'
        x_page_from = '/biblStruct/monogr/imprint/biblScope[@unit="page"]/@from'
        x_page_to = '/biblStruct/monogr/imprint/biblScope[@unit="page"]/@to'
        x_pages = '/biblStruct/monogr/imprint/biblScope[@unit="page"]'
        x_issn = '/biblStruct/monogr/idno[@type="ISSN"]'
        x_isbn = '/biblStruct/monogr/idno[@type="ISBN"]'

        x_date = '/biblStruct/monogr/imprint/date[@type="published"]'
        x_url = '/biblStruct/analytic/ptr[not(@type)]'

        x_meeting_title = '/biblStruct/monogr/meeting/title'
        x_meeting_place = '/biblStruct/monogr/meeting/placeName'
        x_meeting_start = '/biblStruct/monogr/meeting/date[@type="conferenceStartDate"]'
        x_meeting_end = '/biblStruct/monogr/meeting/date[@type="conferenceEndDate"]' 

        # authorship
        x_author_persons = '/biblStruct/analytic/author/persName'

        local_doi = _get_first_value_xpath(root, x_doi)
        if local_doi != None:
            json_bib['DOI'] = local_doi

        # if we have a DOI, we get the CrossRef entry directly
        if 'DOI' in json_bib and json_bib['DOI'] is not None and len(json_bib['DOI']) >0:
            result_glutton = self.biblio_glutton_lookup(doi=json_bib['DOI'])
            if result_glutton != None:
                return result_glutton

        local_pmid = _get_first_value_xpath(root, x_pmid)
        if local_pmid != None:
            json_bib["pmid"] = local_pmid
        
        local_pmcid = _get_first_value_xpath(root, x_pmcid)
        if local_pmcid != None:
            json_bib["pmcid"] = local_pmcid 

        local_url = _get_first_value_xpath(root, x_url)
        if local_url != None:
            json_bib['URL'] = local_url

        json_bib['author'] = _get_all_values_authors_xpath(root, x_author_persons)

        local_volume = _get_first_value_xpath(root, x_volume)
        if local_volume != None:
            json_bib["volume"] = local_volume
        local_issn = _get_first_value_xpath(root, x_issn)
        if local_issn != None:
            json_bib["ISSN"] = local_issn
        local_isbn = _get_first_value_xpath(root, x_isbn)
        if local_isbn != None:
            json_bib["ISBN"] = local_isbn
        local_issue = _get_first_value_xpath(root, x_issue)
        if local_issue != None:
            json_bib["issue"] = local_issue

        local_oa_link = _get_first_attribute_value_xpath(root, x_oa_link)
        if local_oa_link != None:
            json_bib["oaLink"] = local_oa_link

        json_bib["title"] = []
        local_title = _get_first_value_xpath(root, x_title)
        if local_title != None:
            json_bib["title"].append(local_title)
        local_publisher = _get_first_value_xpath(root, x_publisher) 
        if local_publisher != None:
            json_bib["publisher"] = local_publisher

        # date has a strange structure in crossref... we also store the standard ISO 8601 format which is much easier to work with and clear  
        local_date = _get_date_xpath(root, x_date)
        if local_date != None:
            json_bib["date"] = local_date

            parts = []
            date_parts = local_date.split("-")
            if len(date_parts) > 0:
                # year
                parts.append(date_parts[0])
            if len(date_parts) > 1:
                # month
                parts.append(date_parts[1])
            if len(date_parts) > 2:
                # day
                parts.append(date_parts[2])    

            json_bib["published-online"] = { "date-parts": [ parts ] }    
            ''' format is:
            "published-online": {
              "date-parts": [
                [
                  2014,
                  9,
                  8
                ]
              ]
            },
            '''
        page_from = _get_first_attribute_value_xpath(root, x_page_from)
        page_to =  _get_first_attribute_value_xpath(root, x_page_to)
        if page_from is not None and page_to is not None:
            json_bib["page"] = page_from + '-' + page_to
        else:
            local_page_range = _get_first_value_xpath(root, x_pages)
            if local_page_range != None:
                json_bib["page"] = local_page_range

        json_bib["container-title"] = []
        title_journal = _get_first_value_xpath(root, x_journal)
        if title_journal != None and len(title_journal) > 0:
            json_bib["container-title"].append(title_journal)
        title_monograph = _get_first_value_xpath(root, x_monograph)
        if title_monograph != None and len(title_monograph) > 0:
            json_bib["container-title"].append(title_monograph)

        event_title = _get_first_value_xpath(root, x_meeting_title)
        if event_title != None and len(event_title) > 0:
            json_bib["event"] = { "name": event_title } 

        return json_bib

    def wiki_biblio2json(self, entity):
        '''
        For a research publication entity, convert some wikidata information relevant to deduplication into
        bibliographical metadata, similar to CrossRef JSON format (but simplified) and feed the signature index
        '''
        metadata = {}
        local_title = None
        local_first_author = None
        if "claims" in entity:
            for the_property in entity["claims"]:
                claims = entity["claims"][the_property]
                if the_property == "P356":
                    # P356 DOI 
                    if len(claims) > 0 and "value" in claims[0]:
                        local_doi = claims[0]["value"]
                        if local_doi != None and len(local_doi) > 0:
                            metadata["DOI"] = local_doi

                    # DOI index
                    entity["index_doi"] = local_doi.lower()

                    # we can simply get the crossref entry and stop the conversion at this stage
                    metadata = self.biblio_glutton_lookup(doi=local_doi)

                    if metadata != None:
                        if "title" in metadata and "author" in metadata:
                            local_key = self.title_author_key(metadata["title"], metadata["author"])
                            if local_key != None:
                                entity["title_author_key"] = local_key

                        entity["metadata"] = metadata
                        return entity

                elif the_property == "P1476":
                    # P1476 gives the article title
                    if len(claims) > 0 and "value" in claims[0]:
                        if "text" in claims[0]["value"]:
                            local_title = claims[0]["value"]["text"]
                        else:
                            local_title = claims[0]["value"]
                        if local_title != None and len(local_title) > 0:
                            metadata["title"] =  [ local_title ]

                    '''
                    elif "P50" in claim:
                        # P50 (entity value) and P2093 (string value) gives the list of authors
                        # P50 entity value is annoying because it requires an additional web access to get the author string form
                        # in addition the partition of authors into entity value and string value complicates the
                        # retrieval of the order of the authors and exploiting the first author as traditional look-up key
                        if len(claim["P50"]) > 0:
                            for author_claim in claim["P50"]:
                                if "value" in author_claim: 
                                    local_author_entity = author_claim["value"]
                                    # get the author rank


                        # the actual author order is given by the property P1545 (series ordinal) in the qualifiers

                    elif "P2093" in claim:  
                        # unfortunately, the person name string value is raw name string, without identification of 
                        # first/middle/last names
                        if len(claim["P2093"]) > 0:
                            for author_claim in claim["P2093"]:
                                if "value" in author_claim: 
                                    local_author_string = author_claim["value"]
                                    # get the author rank
                    '''

                elif the_property == "P577":
                    # P577 publication date
                    if len(claims) > 0 and "value" in claims[0]:
                        local_date = claims[0]["value"]["time"]
                        # ISO format e.g. "+2002-01-00T00:00:00Z"
                        if local_date.startswith("+"):
                            local_date = local_date[1:]
                        ind = local_date.find("T")
                        if ind != -1:
                            local_date = local_date[:ind]
                        metadata['date'] = local_date

                        parts = []
                        date_parts = local_date.split("-")
                        if len(date_parts) > 0:
                            # year
                            parts.append(date_parts[0])
                        if len(date_parts) > 1:
                            # month
                            parts.append(date_parts[1])
                        if len(date_parts) > 2:
                            # day
                            parts.append(date_parts[2])    

                        metadata["published-online"] = { "date-parts": [ parts ] }    

                elif the_property == "P818": 
                    # P818 arXiv ID
                    if len(claims) > 0 and "value" in claims[0]:
                        local_arxiv = claims[0]["value"]
                        if local_arxiv != None and len(local_arxiv) > 0:
                            metadata["arXiv"] = local_arxiv

                elif the_property == "P698":
                    # P698 PMID
                    if len(claims) > 0 and "value" in claims[0]:
                        local_pmid = claims[0]["value"]
                        if local_pmid != None and len(local_pmid) > 0:
                            metadata["PMID"] = local_pmid

                elif the_property == "P932":
                    # P932 PMC ID
                    if len(claims) > 0 and "value" in claims[0]:
                        local_pmcid = claims[0]["value"]
                        if local_pmcid != None and len(local_pmcid) > 0:
                            metadata["PMID"] = local_pmcid

                # no need to go further

        # set title + first author last name index
        if local_title != None and local_first_author != None:
            entity["index_title_author"] = self.title_author_key(local_title, local_first_author)
    
        entity["metadata"] = metadata

        return entity


    def title_author_key(self, title, author_block):
        '''
        Generate a key for a document hash index based on the title and first author last name. 
        If no key is possible, return None 
        '''
        if title == None or len(title) == 0 or author_block == None or len(author_block) == 0:
            return None

        # normally title is a list, but for safety we cover also a string value
        if isinstance(title, list):
            simplified_title = title[0].replace(" ", "").lower()
        else:
            simplified_title = title.replace(" ", "").lower()

        if "family" in author_block[0]: 
            simplified_name = author_block[0]['family'].replace(" ", "").lower()
            return simplified_title + '_' + simplified_name

        return None

    def register_merging(self, entity1, entity2):
        '''
        Store a merging decision:
        - create or extend the merging list related to the entities
        - index the merging list for the two entities   
        '''

        # check if merging_entities and merging_lists collections exist, if not create them
        if not self.staging_graph.has_vertex_collection('merging_entities'):
            self.merging_entities = self.staging_graph.create_vertex_collection('merging_entities')
        else:
            self.merging_entities = self.staging_graph.vertex_collection('merging_entities')

        if not self.staging_graph.has_vertex_collection('merging_lists'):
            self.merging_lists = self.staging_graph.create_vertex_collection('merging_lists')
        else:
            self.merging_lists = self.staging_graph.vertex_collection('merging_lists')

        # do we have a merging list for one of these entities?
        merging_list1_id = None
        if self.staging_graph.has_vertex("merging_entities/" + entity1['_key']):
            merging_list1_item = self.merging_entities.get("merging_entities/" + entity1['_key'])
            merging_list1_id = merging_list1_item['list_id']

        merging_list2_id = None    
        if self.staging_graph.has_vertex("merging_entities/" + entity2['_key']):
            merging_list2_item = self.merging_entities.get("merging_entities/" + entity2['_key'])
            merging_list2_id = merging_list2_item['list_id']

        if merging_list1_id != None and merging_list2_id != None and merging_list1_id == merging_list2_id:
            # entities already registered for merging, nothing to do...
            return True

        #print(merging_list1_id, merging_list2_id)

        # get the corresponding lists
        merging_list1 = None
        if merging_list1_id != None and self.staging_graph.has_vertex(merging_list1_id):
            merging_list1_item = self.merging_lists.get(merging_list1_id)
            merging_list1 = merging_list1_item['data']

        merging_list2 = None
        if merging_list2_id != None and self.staging_graph.has_vertex(merging_list2_id):
            merging_list2_item = self.merging_lists.get(merging_list2_id)
            merging_list2 = merging_list2_item['data']
        
        if merging_list1 != None and merging_list2 != None:
            # merge the second list into the first one
            for local_entity_id in merging_list2:
                if not local_entity_id in merging_list1:
                    merging_list1.append(local_entity_id)
            merging_list1_item['data'] = merging_list1

            # update first list 
            self.staging_graph.update_vertex(merging_list1_item)

            # update index for all the entities of the second list
            for local_id in merging_list2:
                entity_item = self.merging_entities.get(_project_entity_id_collection(local_id, "merging_entities"))
                entity_item['list_id'] = merging_list1_item['_id']
                entity_item['collection'] = _get_collection_name(local_id)
                self.staging_graph.update_vertex(entity_item)

            # remove second list
            self.staging_graph.delete_vertex(merging_list2_item['_id'])

        if merging_list1 != None and merging_list2 == None:
            # add entity2 into the first list
            if entity2['_id'] not in merging_list1:
                merging_list1.append(entity2['_id'])
            merging_list1_item['data'] = merging_list1

            # update first list
            self.staging_graph.update_vertex(merging_list1_item)

            # update index for entity2
            entity2_item = {}
            entity2_item['_key'] = entity2['_key']
            entity2_item['_id'] = "merging_entities/" + entity2['_key']
            entity2_item['list_id'] = merging_list1_item["_id"]
            entity2_item['collection'] = _get_collection_name(entity2['_id'])
            self.staging_graph.insert_vertex('merging_entities', entity2_item)

        elif merging_list1 == None and merging_list2 != None:
            # add entity1 into the second list
            if not entity1['_id'] in merging_list2:
                merging_list2.append(entity1['_id'])
            merging_list2_item['data'] = merging_list2

            # update second list
            self.staging_graph.update_vertex(merging_list2_item)

            # update index for entity1
            entity1_item = {}
            entity1_item['_key'] = entity1['_key']
            entity1_item['_id'] = "merging_entities/" + entity1['_key']
            entity1_item['list_id'] = merging_list2_item["_id"]
            entity1_item['collection'] = _get_collection_name(entity1['_id'])
            self.staging_graph.insert_vertex('merging_entities', entity1_item)

        elif merging_list1 == None and merging_list2 == None:
            # create a new list
            merging_list = []
            merging_list.append(entity1['_id'])
            merging_list.append(entity2['_id'])
            local_id = self.get_uid()
            merging_list_item = {}
            merging_list_item["_key"] = local_id
            merging_list_item["_id"] = "merging_lists/" + local_id
            merging_list_item['data'] = merging_list

            # insert the new list
            self.staging_graph.insert_vertex('merging_lists', merging_list_item)

            # update index for the 2 entities
            entity1_item = {}
            entity1_item['_key'] = entity1['_key']
            entity1_item['_id'] = "merging_entities/" + entity1['_key']
            entity1_item['list_id'] = merging_list_item["_id"]
            entity1_item['collection'] = _get_collection_name(entity1['_id'])
            self.staging_graph.insert_vertex('merging_entities', entity1_item)

            entity2_item = {}
            entity2_item['_key'] = entity2['_key']
            entity2_item['_id'] = "merging_entities/" + entity2['_key']
            entity2_item['list_id'] = merging_list_item["_id"]
            entity2_item['collection'] = _get_collection_name(entity2['_id'])
            self.staging_graph.insert_vertex('merging_entities', entity2_item)

        return True


def _get_first_value_xpath(node, xpath_exp):
    values = node.xpath(xpath_exp)
    value = None
    if values is not None and len(values)>0:
        value = values[0].text
    return value

def _get_first_attribute_value_xpath(node, xpath_exp):
    values = node.xpath(xpath_exp)
    value = None
    if values is not None and len(values)>0:
        value = values[0]
    return value

def _get_date_xpath(node, xpath_exp):
    dates = node.xpath(xpath_exp)
    date = None
    if dates is not None and len(dates)>0:
        date = dates[0].get("when")
    return date

def _get_all_values_authors_xpath(node, xpath_exp):
    values = node.xpath(xpath_exp)
    result = []
    if values is not None and len(values)>0:
        for val in values:
            # each val is a person
            person = {}
            fornames = val.xpath('./forename')
            surname = val.xpath('./surname')

            if surname != None and len(surname)>0 and surname[0].text != None:
                person['family'] = surname[0].text.strip() 

            if fornames != None:
                for forname in fornames:
                    if forname.text != None:
                        if not 'given' in person:
                            person['given'] = forname.text.strip()
                        else:
                            person['given'] += " " + forname.text
            result.append(person)
    # family, given - there is no middle name in crossref, it is just concatenated to "given" without any normalization
    return result

def _project_entity_id_collection(entity_id, collection_name):
    '''
    Take an entity id and replace the collection prefix with the provided one
    '''
    ind = entity_id.find("/")
    if ind == -1:
        return collection_name+"/"+entity_id
    else:
        return collection_name+entity_id[ind:]


def _get_collection_name(entity_id):
    '''
    return the name of the collection based on the given identifier
    '''
    ind = entity_id.find("/")
    if ind != -1:
        return entity_id[:ind]
    else: 
        return None


def _biblio_glutton_url(biblio_glutton_protocol, biblio_glutton_host, biblio_glutton_port):
    biblio_glutton_base = biblio_glutton_protocol + "://" + biblio_glutton_host
    if biblio_glutton_base.endswith("/"):
        res = biblio_glutton_base[:-1]
    else: 
        res = biblio_glutton_base
    if biblio_glutton_port is not None and biblio_glutton_port>0:
        res += ":"+str(biblio_glutton_port)
    return res+"/service/lookup?"

def _grobid_url(grobid_protocol, grobid_url, grobid_port):
    the_url = grobid_protocol + "://" + grobid_base
    if the_url.endswith("/"):
        the_url = the_url[:-1]
    if grobid_port is not None and grobid_port>0:
        the_url += ":"+str(grobid_port)
    the_url += "/api/"
    return the_url

