from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Request, UploadFile

from config.config_manager import ConfigManager
from core.utils import is_supported


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
        files = filter_supported_uploads(files)

    return app


def filter_supported_uploads(uploaded_files: list[UploadFile]) -> list[UploadFile]:
    validated_files: list[UploadFile] = []

    for file in uploaded_files:
        filename = file.filename or ""
        suffix = Path(filename).suffix.lower()

        if not is_supported(suffix):
            raise ValueError(f"Unsupported file type: {suffix} (in file: {filename})")
        validated_files.append(file)

    return validated_files


def run_api(config_manager: ConfigManager):
    pass
