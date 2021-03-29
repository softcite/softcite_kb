'''
    Common methods for converting entities into external exchange formats 
'''

import json
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
                print(key, " ", converted_key)
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

    return jsonEntity

def _expend_element(jsonEntity, element, lang):
    if element in jsonEntity:
        if not lang in jsonEntity[element]:
            lang_lab_val = jsonEntity[element]
            lang_lab = {}
            lang_lab[lang] = lang_lab_val
            jsonEntity[element] = en_lab
    return jsonEntity

def convert_to_codemeta(kb, entity):
    ''' 
    Conversion into codemeta JsonLD format. Because codemeta describes a resource and not "the resources
    about a resource" as we are doing, we are losing the contradictory and numerical dimensions
    of our representation, and some metadata. 
    '''
    global codemeta_template
    converted = copy.deepcopy(entity)

    # load codemeta template if not already done
    if codemeta_template == None:
        codemeta_template = _load_codemeta_template()

    codemeta_json = copy.deepcopy(codemeta_template)

    return codemeta_json

def _load_codemeta_template():
    json_template = None
    template_file = os.path.join("data", "resources", "codemeta.template.json")
    if not os.path.isfile(template_file): 
        print("Error: template file does not exist for codemeta")
        return None

    with open(template_file) as template_f:
        json_template_string = template_f.read()
        if not source is None:
            json_template_string = json_template_string.replace('[]', '[' + json.dumps(source) + ']')

        json_template = json.loads(json_template_string)

    return json_template
