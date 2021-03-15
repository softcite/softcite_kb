from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()

@router.get("/alive", response_class=PlainTextResponse, tags=["generic"])
def is_alive_status():
    return "true"

@router.get("/version", response_class=PlainTextResponse, tags=["generic"])
def get_version():
    api_settings = get_api_settings()
    return api_settings.version

@router.get("/entities/{identifier}", tags=["entities"])
async def get_software(identifier: str):
    record = {}

    return record

@router.get("/relations/{identifier}", tags=["relations"])
async def get_software(identifier: str):
    record = {}

    return record
