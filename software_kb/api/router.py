from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
import time 

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
    api_settings = get_api_settings()
    return api_settings.version


# generic access

# the value for "collection" of entitites are "software", "documents", "persons", "organizations" and "licenses"
@router.get("/entities/{collection}/{identifier}", tags=["entities"])
async def get_entity(collection: str, identifier: str):
    start_time = time.time()
    if not kb.kb_graph.has_vertex(collection + '/' + identifier):
        raise HTTPException(status_code=404, detail="Entity not found in collection "+collection)
    result = {}
    result['full_count'] = 1
    result['records'] = kb.kb_graph.vertex(collection + '/' + identifier)
    result['runtime'] = round(time.time() - start_time, 3)
    return result

# the value for "collection" of relations are "references", "citations", "actors", "fundings", "dependencies" and "copyrights"
@router.get("/relations/{collection}/{identifier}", tags=["relations"])
async def get_relation(collection: str, identifier: str):
    start_time = time.time()
    if not kb.kb_graph.has_edge(collection + '/' + identifier):
        raise HTTPException(status_code=404, detail="Relation not found in collection "+collection)
    result = {}
    result['full_count'] = 1
    result['records'] = kb.kb_graph.edge(collection + '/' + identifier)
    result['runtime'] = round(time.time() - start_time, 3)
    return result


'''
for returning list of entities or relations, the following parameters are used in every endpoints:  
@ranker with values in ["count", "date"], default value count
@page_rank page number for the list of result, starting at 0
@page_size number of results per page (default is 10)
'''

# get list of values for a "collection" of entitites, one of "software", "documents", "persons", "organizations" and "licenses"
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
@ranker, default value count (return the mentions in the document containing most mentions of this software first)
'''
@router.get("/entities/software/{identifier}/citations", tags=["entities"])
async def get_software(identifier: str, page_rank: int = 0, page_size: int = 10, ranker: str = 'count'):
    start_time = time.time()

    cursor = kb.db.aql.execute(
        'FOR doc IN software LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) + " RETURN doc['_key']"
    )

    if ranker == 'count':
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

    elif ranker == None:
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

    else:
        raise HTTPException(status_code=422, detail="Ranker parameter is unknown: "+ranker)


'''
return all documents mentioning a software, documents are ranked following the parameter 
@ranker, default value count (return the document containing most mentions of this software first)
'''
@router.get("/entities/software/{identifier}/documents", tags=["entities"])
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
@router.get("/entities/document/{identifier}/software", tags=["entities"])
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
    return records


'''
return all the software entities a person has contributed to
'''
@router.get("/entities/person/{identifier}/software", tags=["entities"])
async def get_person_software(identifier: str, page_rank: int = 0, page_size: int = 10, ranker: str = 'count'):
    start_time = time.time()

    cursor = kb.db.aql.execute(
        'FOR actor IN actors '
        + ' FILTER rights._from == "persons/' + identifier + '"'
        + ' && (SPLIT(actor._to, "/", 1)[0]) IN ["software"]'
        + ' COLLECT soft_id = actor._to' 
        + ' LIMIT ' + str(page_rank*page_size) + ', ' + str(page_size) 
        + ' RETURN soft_id', full_count=True)

    # note: aggregated by roles ?

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
    return records

'''
return all the software entities an organization has been involved with via its members 
@ranker, default value count (return first the software with most members of the organization have contributed to)
'''
@router.get("/entities/organization/{identifier}/software", tags=["entities"])
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
    return records


'''
return the n-best references to a software, following the criteria of the CiteAs service 
'''
@router.get("/entities/software/{identifier}/citeas", tags=["entities"])
async def get_software_citeas(identifier: str, n_best: int = 10):
    start_time = time.time()

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
    return records