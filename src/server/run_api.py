import uvicorn
from fastapi import FastAPI, Request, UploadFile

from config.config_manager import ConfigManager


def create_app(config_manager: ConfigManager) -> FastAPI:
    app = FastAPI(title="EPUB to Markdown API")
    app.state.config_manager = config_manager
    return app


def run_api(config_manager: ConfigManager):
    pass
