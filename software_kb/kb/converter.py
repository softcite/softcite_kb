'''
    Common methods for converting entities into external exchange formats.

    Regarding codemeta and jsonld, see https://validator.schema.org/?hl=en-US 
'''

import json
import os
from software_kb.kb.knowledge_base import knowledgeBase
import copy

# manual ranking of source reliability - in the future it should be more case-specific with dedicated ML model(s)
# exploiting the graph
source_prioritization = ["Q2013", "rOpenSci", "CRAN", "Q364", "software-mentions", "grobid"]

def convert_to_simple_format(kb, entity):
    '''
    We replace the Wikidata property names (P**) and the Wikidata entity names by 
    canonical English labels, which will make reading much easier 
    '''
    converted = copy.deepcopy(entity)    
    converted = _convert_to_simple_format_item(kb, converted)

    return converted

def _convert_to_simple_format_item(kb, item):
    if item == None:
        return None
    if isinstance(item, str):
        converted_string = kb.naming_wikidata_string(item)
        if converted_string != None:
            return converted_string
        else:
            return item
    elif isinstance(item, list):
        result = []
        for value in item:
            converted_value = _convert_to_simple_format_item(kb, value)
            if converted_value != None:
                result.append(converted_value)
            else:
                result.append(value)
        return result
    elif isinstance(item, dict):
        result = {}
        for key, value in item.items():
            # conversion can be done both for key and value
            if key.startswith("_"):
                result[key] = value
            else:
                converted_key = kb.naming_wikidata_string(key)
                if converted_key != None:
                    result[converted_key] = _convert_to_simple_format_item(kb, value)
                else:
                    result[key] =  _convert_to_simple_format_item(kb, value)
        return result
    else: 
        return item

def convert_to_wikidata(kb, entity):
    '''
    Conversion to Wikidata vanilla format. The actual format used by the KB is a simplified 
    one, covering only English (thus removing all the multilingual additional nested descriptions)
    and where unused blocks are removed. In addition, numerical information need to be removed.
    '''
    jsonEntity = copy.deepcopy(entity)

    # restore language level
    _expend_element(jsonEntity, "labels", "en")
    _expend_element(jsonEntity, "descriptions", "en")
    _expend_element(jsonEntity, "aliases", "en")

    # recomplexify the "snark" as "value" attribute
    '''
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
    '''

    jsonEntity["type"] = "item"

    return jsonEntity

def _expend_element(jsonEntity, element, lang):
    if element in jsonEntity:
        if not lang in jsonEntity[element]:
            lang_lab_val = jsonEntity[element]
            lang_lab = {}
            lang_lab[lang] = lang_lab_val
            jsonEntity[element] = lang_lab
    return jsonEntity

def convert_to_codemeta(kb, jsonEntity, collection):
    ''' 
    Conversion into codemeta jsonld format. 

    Because codemeta describes a resource and not "the resources about a resource" as we are doing, 
    we are losing the contradictory, aggregation and numerical dimensions of our representation 
    - we need to select the "best" value for a given field. Codemeta is similar to cataloguing a work, 
    it's not about representing usages, connections and these sorts of information.

    A few things are not very clear, for instance nothing to specify user manual and documentation 
    of a software, but we have unclear overlapping things like buildInstructions, readme or requirement 
    properties and softwareHelp in schema.org -> addressed in new version of codemeta

    Unclear: do we describe a software, a software version? a code source release?  

    Anyway we keep the codemeta output relatively simple, translating the main metadata, and avoid
    the usual ontology and metadata marshlands. 
    '''
    if collection == "persons":
        return _person_to_codemeta(jsonEntity, kb, full=True)

    codemeta_json = {}
    codemeta_json["@context"] = [ "https://doi.org/10.5063/schema/codemeta-2.0", "http://schema.org" ]
    codemeta_json["@type"] = [ "SoftwareApplication", "SoftwareSourceCode" ]
    
    if "id" in jsonEntity:
        codemeta_json["identifier"] = jsonEntity['id']
    else:
        codemeta_json["identifier"] = jsonEntity['_id']

    if "summary" in jsonEntity:
        codemeta_json["description"] = jsonEntity['summary']

    if "labels" in jsonEntity:
        if "aliases" in jsonEntity:
            names = jsonEntity["aliases"]
            names.insert(0, jsonEntity['labels'])
            codemeta_json["name"] = names
        else:
            codemeta_json["name"] = jsonEntity['labels']

    '''
    codeRepository  P1324
    programmingLanguage     P277
    runtimePlatform     P400
    downloadUrl     P4945
    fileSize    P3575
    operatingSystem     P306
    softwareRequirements    P1547
    softwareVersion     P348
    author  P50
    citation    P2860
    contributor     P767
    dateCreated     P571
    dateModified    P5017
    datePublished   P577
    editor  P98
    fileFormat  P2701
    funder  P859
    keywords    P921
    license     P275
    producer    P162
    publisher   P123
    isPartOf    P361
    hasPart     P527
    sameAs  P2888
    url     P856 (official URL) then P854 (reference URL)
    givenName   P735
    familyName  P734
    email   P968 
    issueTracker    Q956086
    '''

    if "claims" in jsonEntity:
        for wikidata_property in jsonEntity["claims"]:
            if wikidata_property == 'P1324':
                # codeRepository
                codemeta_json['codeRepository'] = jsonEntity["claims"][wikidata_property][0]['value']
            elif wikidata_property == 'P277':
                # programmingLanguage
                for the_value in jsonEntity["claims"][wikidata_property]:
                    converted_name = kb.naming_wikidata_string(the_value['value'])
                    if converted_name == None:
                        converted_name = the_value['value']
                    # short cut here, we should get these infos from the KB itself normally...
                    codemeta_json['programmingLanguage'] = {}
                    codemeta_json['programmingLanguage']["@type"] = "ComputerLanguage"
                    if converted_name == 'R' or converted_name == 'Q206904':    
                        codemeta_json['programmingLanguage']['name'] = 'R'
                        codemeta_json['programmingLanguage']['url'] = 'https://r-project.org'
                    else:
                        codemeta_json['programmingLanguage']['name'] = converted_name
            elif wikidata_property == 'P400':
                # runtimePlatform ... rather a list
                runtimePlatforms = []
                for the_value in jsonEntity["claims"][wikidata_property]:
                    runtimePlatforms.append(_convert_to_simple_format_item(kb, the_value['value']))
                if len(runtimePlatforms) == 1:
                    codemeta_json['runtimePlatform'] = runtimePlatforms[0]
                elif len(runtimePlatforms) > 1:
                    codemeta_json['runtimePlatform'] = runtimePlatforms
            elif wikidata_property == 'P4945':
                # downloadUrl
                codemeta_json['downloadUrl'] = jsonEntity["claims"][wikidata_property][0]['value']
            elif wikidata_property == 'P3575':
                # fileSize
                codemeta_json['fileSize'] = jsonEntity["claims"][wikidata_property][0]['value']
            elif wikidata_property == 'P306':
                # operatingSystem
                operatingSystems = []
                for the_value in jsonEntity["claims"][wikidata_property]:
                    # possibly a list here
                    operatingSystems.append(_convert_to_simple_format_item(kb, the_value['value']))
                if len(operatingSystems) == 1:
                    codemeta_json['operatingSystem'] = operatingSystems[0]
                elif len(operatingSystems) > 1:
                    codemeta_json['operatingSystem'] = operatingSystems
                '''
                elif wikidata_property == 'P1547':
                    # softwareRequirements

                elif wikidata_property == 'P348':
                    # softwareVersion
                '''

            elif wikidata_property == 'P854' and 'url' not in codemeta_json:
                # url (references)
                best_url = _select_best_value(jsonEntity["claims"][wikidata_property], kb)
                if best_url != None:
                    codemeta_json['url'] = best_url

            elif wikidata_property == 'P856':
                # url (official)
                best_url = _select_best_value(jsonEntity["claims"][wikidata_property], kb)
                if best_url != None:
                    codemeta_json['url'] = best_url


            elif wikidata_property == "P123":
                # publisher
                best_publisher = _select_best_value(jsonEntity["claims"][wikidata_property], kb)
                if best_publisher != None:
                    codemeta_json['publisher'] = best_publisher


            elif wikidata_property == 'P50':
                # author
                authors = []
                for the_value in jsonEntity["claims"][wikidata_property]:
                    # get author id
                    authors.append(the_value['value'])
                if len(authors)>0:
                    codemeta_json["author"] = []
                    for author in authors:
                        # get the person entry, normally available in the local KB
                        record = kb.kb_graph.vertex('persons/' + author)
                        if record:
                            codemeta_json["author"].append(_person_to_codemeta(record, kb))

            elif wikidata_property == 'P767':
                # contributor
                contributors = []
                for the_value in jsonEntity["claims"][wikidata_property]:
                    # get author id
                    contributors.append(the_value['value'])
                if len(contributors)>0:
                    codemeta_json["contributor"] = []
                    for contributor in contributors:
                        # get the person entry, normally available in the local KB
                        record = kb.kb_graph.vertex('persons/' + contributor)
                        if record:
                            codemeta_json["contributor"].append(_person_to_codemeta(record, kb))


            elif wikidata_property == "P275":
                # license (i.e. copyright license)   
                best_license = _select_best_value(jsonEntity["claims"][wikidata_property], kb)
                if best_license != None:
                    codemeta_json['license'] = best_license

            elif wikidata_property == "P2078":
                # this is not in codemeta (nothing on documentation and user manual), but jsonld has property 
                # "documentation" for Web API https://schema.org/documentation (why just for Web API)
                # so it's not valid codemeta, but no alternative apparently
                best_url = _select_best_value(jsonEntity["claims"][wikidata_property], kb)
                if best_url != None:
                    codemeta_json['documentation'] = best_url



    return codemeta_json

def _get_count(the_value_block, source=None):
    '''
    In the given value block, the count is the sum of the count of all the reference 
    sources (if source=None) or a specific source if specified
    '''
    if not "references" in the_value_block:
        return 0
    references = the_value_block["references"]
    total_count = 0
    for reference in references:
        if source == None or ("P248" in reference and "value" in reference["P248"] and reference["P248"]["value"] == source):
            if "P248" in reference and "count" in reference["P248"]:
                total_count += reference["P248"]["count"]
            else:
                total_count += 1
    return total_count

def _select_best_value(the_property_block, kb):
    '''
    Return the best value for a given property based on source and count
    '''
    best_source = None
    best_value = None
    best_value_datatype = None
    for the_value_block in the_property_block:
        # get best source first (using source_prioritization)
        references = the_value_block["references"]
        for reference in references:
            if "P248" in reference and "value" in reference["P248"]:
                if best_source == None or source_prioritization.index(reference["P248"]["value"]) < source_prioritization.index(best_source):
                    best_source = reference["P248"]["value"]

    if best_source != None:
        # for the best source, get highest count
        best_count = 0
        for the_value in the_property_block:
            references = the_value_block["references"]
            for reference in references:
                if "P248" in reference and "value" in reference["P248"]:
                    if reference["P248"]["value"] != best_source:
                        continue
                    local_count = _get_count(the_value, best_source)
                    if local_count > best_count:
                        best_count = local_count
                        best_value = the_value['value']
                        best_value_datatype = the_value['datatype']
    if best_value_datatype == 'wikibase-item':
        best_value = _convert_to_simple_format_item(kb, best_value)
    return best_value

def _rank_values(the_property_block, kb):
    '''
    Return the list of pairs (value, count), ranked by descending count 
    '''
    ranking = []
    for the_value in the_property_block:
        references = the_value["references"]
        for reference in references:
            if "P248" in reference and "value" in reference["P248"]:
                local_count = _get_count(the_value)
                local_value = the_value['value']
                if the_value['datatype'] == 'wikibase-item':
                    local_value = _convert_to_simple_format_item(kb, local_value)
                ranking.append((local_value,local_count))
    ranking.sort(key=lambda x: x[1], reverse=True)
    return ranking

def _person_to_codemeta(person, kb, full=False):
    '''
        {
          "@type": "Person",
          "givenName": "",
          "familyName": "",
          "email": "",
          "@id": ""
        }
    '''
    result = {}
    result["@type"] = "Person"
    if full:
        result["@context"] = "https://schema.org" 

    local_labels = person['labels']
    result["name"] = local_labels

    # P735 / check overlapping with Labels to be safer
    if "P735" in person["claims"]:
        givenName = _select_best_value(person["claims"]["P735"], kb)
        result["givenName"] = givenName

    # P734 / check overlapping with Labels to be safer
    if "P734" in person["claims"]:
        familyName = _select_best_value(person["claims"]["P734"], kb)
        result["familyName"] = familyName
    
    # P968
    if "P968" in person["claims"]:
        best_email = _select_best_value(person["claims"]["P968"], kb)
        ranking = _rank_values(person["claims"]["P968"], kb)
        print(ranking)
        emails = []
        if best_email != None:
            emails.append(best_email)
        for the_pair in ranking:
            if the_pair[0] not in emails:
                emails.append(the_pair[0])
        if len(emails) == 1:
            result["email"] = emails[0]
        else:
            result["email"] = emails[0:2]

    # P496 Codemeta puts the orcid id in the @id
    if "P496" in person["claims"]:
        orcid = _select_best_value(person["claims"]["P496"], kb)
        result["@id"] = "https://orcid.org/" + orcid

    return result

def _load_codemeta_template():
    json_template = None
    template_file = os.path.join("data", "resources", "codemeta.template.json")
    if not os.path.isfile(template_file): 
        print("Error: template file does not exist for codemeta")
        return None

    with open(template_file) as template_f:
        json_template_string = template_f.read()
        json_template = json.loads(json_template_string)

    return json_template
