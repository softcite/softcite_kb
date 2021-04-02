import sys
import os
import uvicorn
from typing import Optional
from fastapi import FastAPI, Response
from pydantic import BaseModel
from pydantic import BaseSettings
import pyfiglet
from functools import lru_cache
from software_kb.kb.knowledge_base import knowledgeBase
import yaml
import argparse
from pathlib import Path
from router import router, set_kb

'''
    The web API uses the FastAPI framework. 
'''

tags_metadata = [
    {
        "name": "generic",
        "description": "general information on the web service"
    },
    {
        "name": "entities",
        "description": "retrieve information about knowledge base entities"
    },
    {
        "name": "relations",
        "description": "retrieve information about relations between knowledge base entities"
    },
    {
        "name": "recommenders",
        "description": "filter and predict information about knowledge base entities"
    }
]

kb = None

'''
    Note: managing config is a bit complicated because FastAPI supports a configuration via
    environment variable, so as we want to centralize a complex configuration via nested structures
    in a single place/file for all our platform (that can be mounted to a docker image), we have 
    to extract the API-specific setting parameters from the config file. 
'''

def get_app(server_config) -> FastAPI:
    # the setting specific to the API service (normally one different for dev, test and prod)

    server = FastAPI(
        title=server_config['name'], 
        description=server_config['description'], 
        version=server_config['version'],
        openapi_tags=tags_metadata)
    set_kb(kb)
    server.include_router(router, prefix=server_config['api_route'])

    @server.on_event("startup")
    async def startup_message() -> None:
        ascii_banner = pyfiglet.figlet_format("Software KB API")
        print(ascii_banner)

    @server.on_event("shutdown")
    async def shutdown() -> None:
        print("Software Knowledge Base API service stopped")

    return server

def init_kb(config_path):
    # init the API app after getting the different configuration information
    # the KB settings
    global kb
    kb = knowledgeBase(config_path=config_path)
    #kb.init(config_path=config_path,reset=False)

def load_server_config(config_path):
    yaml_settings = dict()

    yaml_config_file = os.path.abspath(config_path)
    with open(yaml_config_file) as f:
        yaml_settings.update(yaml.load(f, Loader=yaml.FullLoader))

    return yaml_settings['api']

if __name__ == '__main__':
    # stand alone mode, run the application
    parser = argparse.ArgumentParser(
        description="Run the Software Knowledge Base API service.")
    parser.add_argument("--host", type=str, default='0.0.0.0',
                        help="host of the service")
    parser.add_argument("--port", type=str, default=8080,
                        help="port of the service")

    parser.add_argument("--config", type=Path, required=False, help="configuration file to be used", default='./config.yaml')

    args = parser.parse_args()
    config_path = args.config
    
    # unfortunately we can't pass the config file path to the app init, because the app has to be initialized before 
    # the root are defined
    init_kb(config_path)

    # use uvicorn to serve the app, we again have to set the configuration parameters outside the app because uvicorn is an independent layer
    server_config = load_server_config(config_path)

    app = get_app(server_config)

    uvicorn.run(app, 
        port=server_config['port'], 
        host=server_config['host'], 
        reload=server_config['reload'], 
        #workers=server_config['nb_workers'], 
        log_level=server_config['log_level'])
