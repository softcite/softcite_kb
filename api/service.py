import uvicorn
from typing import Optional
from fastapi import FastAPI, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

tags_metadata = [
    {
        "name": "generic",
        "description": "general information on the web service",
    }
]

app = FastAPI(
    title="Software KB web API",
    description="Web API for the Software KB",
    version="0.1.0",
    openapi_tags=tags_metadata
)

@app.get("/alive", response_class=PlainTextResponse, tags=["generic"])
def is_alive_status():
    return "true"

@app.get("/version", response_class=PlainTextResponse, tags=["generic"])
def get_version():
    return "0.1.0"

if __name__ == '__main__':
    # stand alone mode, run the application
    uvicorn.run(app)


