from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse, RedirectResponse
import time 
from software_kb.kb.converter import convert_to_simple_format, convert_to_wikidata, convert_to_codemeta
from enum import Enum
import httpx

router = APIRouter()

kb = None

def set_kb(global_kb):
    global kb
    kb = global_kb

@router.get("/alive", response_class=PlainTextResponse, tags=["generic"])
def is_alive_status():
    return "true"

@router.get("/version", response_class=PlainTextResponse, tags=["generic"])
def get_version():
    api_settings = kb.config['api']
    return api_settings['version']

# to redirect the static /api/frontend/ to  /api/frontend/index.html
@router.get("/frontend", response_class=RedirectResponse, include_in_schema=False)
def static_root():
    return RedirectResponse(url="/frontend/index.html")

# to redirect the static /api/frontend/ to  /api/frontend/index.html
@router.get("/frontend/", response_class=RedirectResponse, include_in_schema=False)
def static_root_():
    return RedirectResponse(url="/frontend/index.html")

# to redirect root favicon
@router.get("/favicon.ico", response_class=RedirectResponse, include_in_schema=False)
def static_root_():
    return RedirectResponse(url="/frontend/data/images/favicon.ico")

# generic access
class Collection(str, Enum):
    software = "software"
    documents = "documents"
    persons = "persons"
    organizations = "organizations"
    licenses = "licenses"


# the value for "collection" of entitites are "software", "documents", "persons", "organizations" and "licenses"
@router.get("/entities/{collection}/{identifier}", tags=["entities"])
async def get_entity(collection: Collection, identifier: str, format: str = 'internal'):
    the_collection = collection.value
    start_time = time.time()
    if not kb.kb_graph.has_vertex(the_collection + '/' + identifier):
        raise HTTPException(status_code=404, detail="Entity not found in collection "+the_collection)
    result = {}
    result['full_count'] = 1

    record = kb.kb_graph.vertex(the_collection + '/' + identifier)

    # we inject the information stored in relations actors, copyrights, funding (other relation-based information 
    # have their dedicated routes - for instance for software sub-routes citations and dependencies)
    if the_collection == 'software' or the_collection == 'documents':

        # actors
        cursor = kb.db.aql.execute(
            'FOR actor IN actors \
                FILTER actor._to == "software/' + identifier + '" \
                RETURN actor')

        for actor in cursor:
            # get the role of the person
            if "claims" in actor:
                for property_key in actor["claims"]:
                    # only one value for the property in actor relation
                    property_value = actor["claims"][property_key][0]

                    # get the person entity
                    local_person_id = actor["_from"]
                    #local_person = kb.kb_graph.vertex('person/' + identifier)
                    property_value['value'] = local_person_id
                    property_value['datatype'] = 'internal-id'

                    # add the property value in the entity
                    if not property_key in record["claims"]:
                        record["claims"][property_key] = []
                    record["claims"][property_key].append(property_value)

        # copyrights
        '''
        cursor = kb.db.aql.execute(
            'FOR copyright IN copyrights \
                FILTER copyright._to == "software/' + identifier + '" \
                RETURN copyright')

        # funding
        cursor = kb.db.aql.execute(
            'FOR fund IN funding \
                FILTER fund._to == "software/' + identifier + '" \
                RETURN fund')
        '''        

    # removing all the local index field
    key_to_remove = []
    for key, value in record.items():
        if key.startswith("index_"):
            key_to_remove.append(key)
    for key in key_to_remove:
        del record[key]

    result['record'] = _convert_target_format(record, collection, format)
    result['runtime'] = round(time.time() - start_time, 3)
    return result

# the value for "relations" are "references", "citations", "actors", "funding", "dependencies" and "copyrights"
@router.get("/relations/{relations}/{identifier}", tags=["relations"])
async def get_relation(relations: str, identifier: str, format: str = 'internal'):
    start_time = time.time()
    if not kb.kb_graph.has_edge(relations + '/' + identifier):
        raise HTTPException(status_code=404, detail="Relation not found in "+relations)
    result = {}
    result['full_count'] = 1
    result['record'] = _convert_target_format(kb.kb_graph.edge(relations + '/' + identifier), relations, format)
    result['runtime'] = round(time.time() - start_time, 3)
    return result


'''
for returning list of entities or relations, the following parameters are used in every endpoints:  
@ranker with values in ["count", "date"], default value count
@page_rank page number for the list of result, starting at 0
@page_size number of results per page (default is 10)
'''

# get list of software ranked by their number of mentions
# default ranker is per count of relations from or to the entity
@router.get("/entities/software", tags=["entities"])
async def get_software(page_rank: int = 0, page_size: int = 10, ranker: str = 'count'):
    start_time = time.time()

    if ranker == 'count':
        cursor = kb.db.aql.execute(
            'FOR mention IN citations \
                COLLECT software_id = mention._to WITH COUNT INTO counter \
                SORT counter DESC ' 
                + ' LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size)
                + ' RETURN {_id: software_id, mentions: counter}', full_count=True)
        result = {}
        records = []
        stats = cursor.statistics()
        if 'fullCount' in stats:
            result['full_count'] = stats['fullCount']
        result['page_rank'] = page_rank
        result['page_size'] = page_size
        for entity in cursor:
            records.append(entity)
        result['records'] = records
        result['runtime'] = round(time.time() - start_time, 3)
        return result

    elif ranker == None:
        cursor = kb.db.aql.execute(
            'FOR soft IN software '
            + ' LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) 
            + ' RETURN soft._id', full_count=True)
        result = {}
        records = []
        stats = cursor.statistics()
        if 'fullCount' in stats:
            result['full_count'] = stats['fullCount']
        result['page_rank'] = page_rank
        result['page_size'] = page_size
        for entity in cursor:
            records.append(entity)
        result['records'] = records
        result['runtime'] = round(time.time() - start_time, 3)
        return result

    #elif ranker == 'date':

    else:
        raise HTTPException(status_code=422, detail="Ranker parameter is unknown: "+ranker)


'''
return all mentions for a software, mentions are ranked following the parameter 
@ranker, default value 'count': return the mentions in the document containing most mentions of this software first
@ranker, value 'group_by_document': return mentions group by document, with document containing most mentions of 
         this software first
'''
@router.get("/entities/software/{identifier}/mentions", tags=["relations"])
async def get_software_mentions(identifier: str, page_rank: int = 0, page_size: int = 10, ranker: str = 'count'):
    start_time = time.time()

    '''
    cursor = kb.db.aql.execute(
        'FOR doc IN software LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) + " RETURN doc['_key']"
    )
    '''

    if ranker == 'count' or ranker == None:
        cursor = kb.db.aql.execute(
            'FOR mention IN citations '
            + ' FILTER mention._to == "software/' + identifier + '"'
            + ' LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size)
            + ' RETURN mention._id', full_count=True)
        result = {}
        records = []
        stats = cursor.statistics()
        if 'fullCount' in stats:
            result['full_count'] = stats['fullCount']
        result['page_rank'] = page_rank
        result['page_size'] = page_size
        for entity in cursor:
            records.append(entity)
        result['records'] = records
        result['runtime'] = round(time.time() - start_time, 3)
        return result

    elif ranker == 'group_by_document':
        cursor = kb.db.aql.execute(
            'FOR mention IN citations '
            + ' FILTER mention._to == "software/' + identifier + '"'
            + ' COLLECT document_id = mention._from INTO mentionsByDocument'
            + ' SORT LENGTH(mentionsByDocument) DESC'
            + ' LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size)
            + ' RETURN { "document_id" : document_id, "nb_doc_mentions": LENGTH(mentionsByDocument), "mentions": mentionsByDocument[*].mention._id }', full_count=True)

        result = {}
        records = []
        stats = cursor.statistics()
        if 'fullCount' in stats:
            result['full_count'] = stats['fullCount']
        result['page_rank'] = page_rank
        result['page_size'] = page_size
        for entity in cursor:
            records.append(entity)
        result['records'] = records
        result['runtime'] = round(time.time() - start_time, 3)
        return result

    else:
        raise HTTPException(status_code=422, detail="Ranker parameter is unknown: "+ranker)


'''
return all depedencies for a given software
'''
@router.get("/entities/software/{identifier}/dependencies", tags=["relations"])
async def get_dependencies(identifier: str, page_rank: int = 0, page_size: int = 10, ranker: str = 'count'):
    start_time = time.time()

    cursor = kb.db.aql.execute(
            'FOR dependency IN dependencies '
            + ' FILTER dependency._from == "software/' + identifier + '"'
            + ' LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size)
            + ' RETURN dependency._to', full_count=True)

    result = {}
    records = []
    stats = cursor.statistics()
    if 'fullCount' in stats:
        result['full_count'] = stats['fullCount']
    result['page_rank'] = page_rank
    result['page_size'] = page_size
    for entity in cursor:
        records.append(entity)
    result['records'] = records
    result['runtime'] = round(time.time() - start_time, 3)

    return result


'''
return all reverse depedencies for a software, so all the software depending on the given software
'''
@router.get("/entities/software/{identifier}/reverse_dependencies", tags=["relations"])
async def get_reverse_dependencies(identifier: str, page_rank: int = 0, page_size: int = 10, ranker: str = 'count'):
    start_time = time.time()

    cursor = kb.db.aql.execute(
            'FOR dependency IN dependencies '
            + ' FILTER dependency._to == "software/' + identifier + '"'
            + ' LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size)
            + ' RETURN dependency._from', full_count=True)

    result = {}
    records = []
    stats = cursor.statistics()
    if 'fullCount' in stats:
        result['full_count'] = stats['fullCount']
    result['page_rank'] = page_rank
    result['page_size'] = page_size
    for entity in cursor:
        records.append(entity)
    result['records'] = records
    result['runtime'] = round(time.time() - start_time, 3)

    return result



'''
return all documents mentioning a software, documents are ranked following the parameter 
@ranker, default value count (return the document containing most mentions of this software first)
'''
@router.get("/entities/software/{identifier}/documents", tags=["relations"])
async def get_software_documents(identifier: str, page_rank: int = 0, page_size: int = 10, ranker: str = 'count'):
    start_time = time.time()

    cursor = kb.db.aql.execute(
        'FOR mention IN citations '
        + ' FILTER mention._to == "software/' + identifier + '"'
        + ' COLLECT doc_id = mention._from' 
        + ' LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) 
        + ' RETURN doc_id', full_count=True)

    result = {}
    records = []
    stats = cursor.statistics()
    if 'fullCount' in stats:
        result['full_count'] = stats['fullCount']
    result['page_rank'] = page_rank
    result['page_size'] = page_size
    for entity in cursor:
        records.append(entity)
    result['records'] = records
    result['runtime'] = round(time.time() - start_time, 3)

    return result

'''
return all the software entities, mentioned in a particular paper, ranked following the parameter 
@ranker, default value count (return first the software with most mentions in the document)
'''
@router.get("/entities/documents/{identifier}/software", tags=["relations"])
async def get_document_software(identifier: str, page_rank: int = 0, page_size: int = 10, ranker: str = 'count'):
    start_time = time.time()

    cursor = kb.db.aql.execute(
        'FOR mention IN citations '
        + ' FILTER mention._from == "documents/' + identifier + '"'
        + ' COLLECT soft_id = mention._to' 
        + ' LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) 
        + ' RETURN soft_id', full_count=True)
    result = {}
    records = []
    stats = cursor.statistics()
    if 'fullCount' in stats:
        result['full_count'] = stats['fullCount']
    result['page_rank'] = page_rank
    result['page_size'] = page_size
    for entity in cursor:
        records.append(entity)
    result['records'] = records
    result['runtime'] = round(time.time() - start_time, 3)

    return result


'''
return all documents ranked by their number of software mentions
'''
@router.get("/entities/documents", tags=["entities"])
async def get_documents(page_rank: int = 0, page_size: int = 10):
    start_time = time.time()
    cursor = kb.db.aql.execute(
        'FOR mention IN citations \
            COLLECT document_id = mention._from WITH COUNT INTO counter \
            SORT counter DESC ' 
            + ' LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size)
            + ' RETURN {_id: document_id, mentions: counter}', full_count=True)
    result = {}
    records = []
    stats = cursor.statistics()
    if 'fullCount' in stats:
        result['full_count'] = stats['fullCount']
    result['page_rank'] = page_rank
    result['page_size'] = page_size
    for entity in cursor:
        records.append(entity)
    result['records'] = records
    result['runtime'] = round(time.time() - start_time, 3)
    return result


'''
return all persons ranked by their number of contributions to software
'''
@router.get("/entities/persons", tags=["entities"])
async def get_persons(page_rank: int = 0, page_size: int = 10):
    start_time = time.time()
    cursor = kb.db.aql.execute(
        'FOR actor IN actors \
            COLLECT person_id = actor._from WITH COUNT INTO counter \
            SORT counter DESC ' 
            + ' LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size)
            + ' RETURN {_id: person_id, contributions: counter}', full_count=True)
    result = {}
    records = []
    stats = cursor.statistics()
    if 'fullCount' in stats:
        result['full_count'] = stats['fullCount']
    result['page_rank'] = page_rank
    result['page_size'] = page_size
    for entity in cursor:
        records.append(entity)
    result['records'] = records
    result['runtime'] = round(time.time() - start_time, 3)
    return result


'''
Return all the software entities a person has contributed to.
For each software, we indicate the person role. 
'''
@router.get("/entities/persons/{identifier}/software", tags=["relations"])
async def get_person_software(identifier: str, page_rank: int = 0, page_size: int = 10, ranker: str = 'count'):
    start_time = time.time()

    cursor = kb.db.aql.execute(
        'FOR actor IN actors '
        + ' FILTER actor._from == "persons/' + identifier + '"'
        + ' && (SPLIT(actor._to, "/", 1)[0]) IN ["software"]'
        + ' COLLECT soft_id = actor._to, the_role = actor["claims"]' 
        + ' LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) 
        + ' RETURN { soft_id, the_role }', full_count=True)

    result = {}
    records = []
    stats = cursor.statistics()
    if 'fullCount' in stats:
        result['full_count'] = stats['fullCount']
    result['page_rank'] = page_rank
    result['page_size'] = page_size
    for entity in cursor:
        record = {}
        record['_id'] = entity['soft_id']
        # get the role of the person regarding the software work
        roles = []
        if "the_role" in entity:
            for key in entity["the_role"]:
                role = kb.relator_role_wikidata(key)
                if role != None:
                    roles.append(role)

        if len(roles) > 0:
            record['roles'] = roles

        records.append(record)
    result['records'] = records
    result['runtime'] = round(time.time() - start_time, 3)
    
    return result

'''
Return all the mentions of the software entities a person has contributed to.
default ranking: return the mentions for the software containing most mentions first
'''
@router.get("/entities/persons/{identifier}/mentions", tags=["relations"])
async def get_person_mentions(identifier: str, page_rank: int = 0, page_size: int = 10, ranker: str = 'count'):
    start_time = time.time()

    cursor = kb.db.aql.execute(
        'FOR actor IN actors '
                    + ' FILTER actor._from == "persons/' + identifier + '" && (SPLIT(actor._to, "/", 1)[0]) IN ["software"] '
                    + ' FOR mention IN citations '
                    + '    FILTER mention._to == actor._to '
                    + '    LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size)
                    + '    RETURN DISTINCT mention._id ', full_count=True)

    result = {}
    records = []
    stats = cursor.statistics()
    if 'fullCount' in stats:
        result['full_count'] = stats['fullCount']
    result['page_rank'] = page_rank
    result['page_size'] = page_size
    for entity in cursor:
        records.append(entity)
    result['records'] = records
    result['runtime'] = round(time.time() - start_time, 3)
    return result


'''
return all the software entities an organization has been involved with via its members 
@ranker, default value count (return first the software with most members of the organization have contributed to)
'''
@router.get("/entities/organizations/{identifier}/software", tags=["relations"])
async def get_organization_software(identifier: str, page_rank: int = 0, page_size: int = 10, ranker: str = 'count'):
    start_time = time.time()

    cursor = kb.db.aql.execute(
        'FOR rights IN copyrights '
        + ' FILTER rights._from == "organizations/' + identifier + '"'
        + ' COLLECT soft_id = mention._to' 
        + ' LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) 
        + ' RETURN soft_id', full_count=True)
    result = {}
    records = []
    stats = cursor.statistics()
    if 'fullCount' in stats:
        result['full_count'] = stats['fullCount']
    result['page_rank'] = page_rank
    result['page_size'] = page_size
    for entity in cursor:
        records.append(entity)
    result['records'] = records
    result['runtime'] = round(time.time() - start_time, 3)
    
    return result


'''
return the n-best references to a software, following the criteria of the CiteAs service 
'''
@router.get("/entities/software/{identifier}/citeas", tags=["recommenders"])
async def get_software_citeas(identifier: str, n_best: int = 10):
    start_time = time.time()

    if not kb.kb_graph.has_vertex('software/' + identifier):
        raise HTTPException(status_code=404, detail="Software entity not found")

    records1 = []
    # do we have a reference directly from this software? these are the best, developer requested citations
    # usually none or very few
    cursor = kb.db.aql.execute(
        'FOR reference IN references '
        + ' FILTER reference._from == "software/' + identifier + '"'
        + ' COLLECT doc_id = reference._to, source_id = reference["claims"]["P2860"][0]["references"][0]["P248"]["value"]' 
        + ' LIMIT ' + str(n_best)
        + ' RETURN { document: doc_id, sources: [source_id] }', full_count=True)

    for entity in cursor:
        records1.append(entity)

    records2 = []
    # do we have a reference from mention context of this software? 
    cursor = kb.db.aql.execute(
        'FOR reference IN references '
        + ' FILTER reference.index_software == "software/' + identifier + '"'
        + ' COLLECT doc_id = reference._to, source_id = reference["claims"]["P2860"][0]["references"][0]["P248"]["value"]'
        + ' WITH COUNT INTO group_size ' 
        + ' SORT group_size DESC'
        + ' LIMIT ' + str(n_best)
        + ' RETURN { document: doc_id, size: group_size, sources: ["software-mentions"]}', full_count=True)

    # note: we might want to consider possible publications present in the imported Wikidata software entities too

    for entity in cursor:
        records2.append(entity)

    result = {}
    records = []

    # merge the lists
    for record1 in records1:
        # check if present in records2
        for record2 in records2:
            if record2['_id'] == record1['_id']:
                # merge
                record1['sources'].extend(record2['sources'])
                break
        records.append(record1)

    for record2 in records2:
        records.append(record2)

    stats = cursor.statistics()
    result['count'] = n_best
    
    result['records'] = records[:n_best]
    result['runtime'] = round(time.time() - start_time, 3)
    return result


'''
Mapper to elasticsearch service 
'''
@router.post("/search/{path:path}", tags=["search"])
async def search_request(path: str, request: Request):
    async with httpx.AsyncClient() as client:
        es_host = kb.config["elasticsearch"]["host"]
        if es_host == None or len(es_host.strip()) == 0:
            es_host = "localhost"
        es_port = kb.config["elasticsearch"]["port"]
        if es_port != None:
            es_port = ":" + str(es_port)
        else:
            es_port = ""
        headers = { "content-type": "application/json" }
        proxy = await client.post("http://"+es_host+es_port+"/"+path, headers=headers, json=await request.json())
    response = Response(proxy.content, status_code=proxy.status_code, media_type="application/json; charset=UTF-8")
    return response

@router.get("/search/{path:path}", tags=["search"])
async def search_request(path: str, request: Request):
    async with httpx.AsyncClient() as client:
        es_host = kb.config["elasticsearch"]["host"]
        if es_host == None or len(es_host.strip()) == 0:
            es_host = "localhost"
        es_port = kb.config["elasticsearch"]["port"]
        if es_port != None:
            es_port = ":" + str(es_port)
        else:
            es_port = ""
        proxy = await client.get("http://"+es_host+es_port+"/"+path, params=request.query_params)
    response = Response(proxy.content, status_code=proxy.status_code, media_type="application/json; charset=UTF-8")
    return response

def _convert_target_format(kb_object, collection, format="simple"):
    if format == 'internal':
        return kb_object
    else:
        if format == 'simple':
            return convert_to_simple_format(kb, kb_object)
        elif format == 'wikidata':
            return convert_to_wikidata(kb, kb_object)
        elif format == 'codemeta':
            return convert_to_codemeta(kb, kb_object, collection)

    