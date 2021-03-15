from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

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

@router.get("/entities/{collection}/{identifier}", tags=["entities"])
async def get_software(collection: str, identifier: str):
    record = kb.kb_graph.vertex(collection + '/' + identifier)
    return record

@router.get("/relations/{collection}/{identifier}", tags=["relations"])
async def get_software(identifier: str):
    record = kb.kb_graph.edge(collection + '/' + identifier)
    return record
