import logging

import uvicorn
from fastapi import FastAPI

from config.config_manager import ConfigManager
from server.routes import router as api_router

logger = logging.getLogger(__name__)


def create_app(config_manager: ConfigManager) -> FastAPI:
    app_config_data = config_manager.toml_data
    app = FastAPI(
        title=app_config_data.get("project", {}).get("name", "Unknown"),
        description=app_config_data.get("project", {}).get("description", "Unknown"),
        version=app_config_data.get("project", {}).get("version", "Unknown"),
    )
    app.state.config_manager = config_manager
    app.include_router(api_router)

    return app


def run_api(config_manager: ConfigManager, host: str = "0.0.0.0", port: int = 8000):
    app = create_app(config_manager)
    uvicorn.run(app, host=host, port=port)
