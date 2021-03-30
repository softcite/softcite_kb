'''
    Common methods for converting entities into external exchange formats 
'''

import json
import os
from software_kb.kb.knowledge_base import knowledgeBase
import copy

codemeta_template = None

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
    and where unused blocks are removed.
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

def convert_to_codemeta(kb, entity):
    ''' 
    Conversion into codemeta JsonLD format. Because codemeta describes a resource and not "the resources
    about a resource" as we are doing, we are losing the contradictory and numerical dimensions
    of our representation, and some metadata. 
    '''
    global codemeta_template
    jsonEntity = copy.deepcopy(entity)

    # load codemeta template if not already done
    if codemeta_template == None:
        codemeta_template = _load_codemeta_template()

    codemeta_json = copy.deepcopy(codemeta_template)

    if "labels" in jsonEntity:
        codemeta_json["identifier"] = jsonEntity['labels']

    if "summary" in jsonEntity:
        codemeta_json["description"] = jsonEntity['summary']

    if "descriptions" in jsonEntity:
        codemeta_json["name"] = jsonEntity['descriptions']

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
    url     P856
    givenName   P735
    familyName  P734
    email   P968 
    issueTracker    Q956086
    '''

    if "claims" in jsonEntity:
        for wikidata_property in jsonEntity["claims"]:
            if wikidata_property == 'P1324':
                # codeRepository
                codemeta_json['codeRepository'] = jsonEntity["claims"][wikidata_property]['value']
            elif wikidata_property == 'P277':
                # programmingLanguage
                converted_name = kb.naming_wikidata_string(jsonEntity["claims"][wikidata_property]['value'])
                if converted_name == None:
                    converted_name = jsonEntity["claims"][wikidata_property]['value']
                # short cut here, we should get these infos from the KB itself normally...
                if converted_name == 'R' or converted_name == 'Q206904':
                    codemeta_json['programmingLanguage']['name'] = 'R'
                    codemeta_json['programmingLanguage']['name']['url'] = 'https://r-project.org'
                else:
                    codemeta_json['programmingLanguage']['name'] = converted_name
            elif wikidata_property == 'P400':
                # runtimePlatform
                codemeta_json['runtimePlatform'] = jsonEntity["claims"][wikidata_property]['value']
            elif wikidata_property == 'P4945':
                # downloadUrl
                codemeta_json['downloadUrl'] = jsonEntity["claims"][wikidata_property]['value']
            elif wikidata_property == 'P3575':
                # fileSize
                codemeta_json['fileSize'] = jsonEntity["claims"][wikidata_property]['value']
            elif wikidata_property == 'P306':
                # operatingSystem
                # I would put a list here, but it's a string apparently (or maybe it's more generic than I think)
                codemeta_json['operatingSystem'] = jsonEntity["claims"][wikidata_property]['value']
                
                '''
                elif wikidata_property == 'P1547':
                    # softwareRequirements

                elif wikidata_property == 'P348':
                    # softwareVersion
                '''

            elif wikidata_property == 'P854':
                # url
                # project/homepage URL is not directly covered by the codemeta term description, but in usual jsonld
                # this is the 'url' attribute at top level
                codemeta_json['url'] = jsonEntity["claims"][wikidata_property]['value']


            # some information are obtained via the relations, e.g. authors, contributors, etc. and for codemeta output
            # we need to access related entities

            elif wikidata_property == 'P50':
                # author
                authors = []

            elif wikidata_property == 'P767':
                # contributor
                contributors = []


    # clean remaining empty fields from the template

    return codemeta_json

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
