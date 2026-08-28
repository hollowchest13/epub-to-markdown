import uvicorn
from fastapi import FastAPI, File, Request, UploadFile

from config.config_manager import ConfigManager
from core.utils import filter_supported_files


def create_app(config_manager: ConfigManager) -> FastAPI:
    app_config_data = config_manager.toml_data
    app = FastAPI(
        title=app_config_data.get("project", {}).get("name", "Unknown"),
        description=app_config_data.get("project", {}).get("description", "Unknown"),
        version=app_config_data.get("project", {}).get("version", "Unknown"),
    )
    output_dir = config_manager.output_dir
    app.state.config_manager = config_manager

    @app.post("/convert")
    async def convert(files: list[UploadFile] | None = None):
        if files is None:
            return {"error": "Files not loaded"}
        files = filter_supported_files(files)

    return app


def filter_uploaded_files(uploaded_files: list[UploadFile]) -> list[UploadFile]:

    return valid_files


def run_api(config_manager: ConfigManager):
    pass
