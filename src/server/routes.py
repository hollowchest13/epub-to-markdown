import asyncio
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from google import genai

from core.converter import convert_to_md
from errors import NetworkError
from server.api_utils import adapt_upload_files, filter_supported_uploads

router = APIRouter()


def _run_conversion(
    tmp_paths: list[Path], client: genai.Client, request_dir: Path, config_manager
):
    """Performs synchronous file conversion (for execution in the executor)."""
    convert_to_md(
        config_manager=config_manager,
        files=tmp_paths,
        client=client,
        target_dir=request_dir,
    )


def _cleanup_temp_files(tmp_paths: list[Path], request_dir: Path):
    """Cleans up temporary files and directories upon completion."""
    for path in tmp_paths:
        path.unlink(missing_ok=True)
    shutil.rmtree(request_dir, ignore_errors=True)


def _create_result_archive(request_dir: Path, tmp_paths: list[Path]) -> Path:
    """Packages generated Markdown files into a ZIP archive saved directly on disk."""
    zip_path = request_dir / "converted.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for tmp_path in tmp_paths:
            result_dir = request_dir / tmp_path.stem
            if result_dir.exists():
                folder_name = tmp_path.stem

                for md_file in result_dir.rglob("*.md"):
                    arc_path = Path(folder_name) / md_file.relative_to(result_dir)
                    zf.write(md_file, arc_path)
    return zip_path


def _file_stream_generator(zip_path: Path, tmp_paths: list[Path], request_dir: Path):
    """Streams the ZIP file chunk by chunk and safely cleans up temporary files after delivery."""
    try:
        with open(zip_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk
    finally:
        for path in tmp_paths:
            path.unlink(missing_ok=True)
        shutil.rmtree(request_dir, ignore_errors=True)


@router.post("/convert")
async def convert(
    request: Request,
    files: Annotated[list[UploadFile], File()],
    x_api_key: Annotated[str, Header()],
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    supported = filter_supported_uploads(files)
    if not supported:
        raise HTTPException(status_code=400, detail="No supported files provided")

    config_manager = request.app.state.config_manager
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, lambda: config_manager.validate_key(x_api_key))
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Gemini API key")
    except NetworkError:
        raise HTTPException(status_code=503, detail="Internet connection error")

    tmp_paths = await adapt_upload_files(supported)

    client = genai.Client(api_key=x_api_key)
    request_dir = config_manager.output_dir / str(uuid.uuid4())
    request_dir.mkdir(parents=True, exist_ok=True)

    try:
        await loop.run_in_executor(
            None,
            lambda: _run_conversion(tmp_paths, client, request_dir, config_manager),
        )

        zip_path = await loop.run_in_executor(
            None, lambda: _create_result_archive(request_dir, tmp_paths)
        )

        return StreamingResponse(
            _file_stream_generator(zip_path, tmp_paths, request_dir),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=converted.zip"},
        )
    except Exception:
        _cleanup_temp_files(tmp_paths, request_dir)
        raise


@router.get("/health")
async def health():
    return {"status": "ok"}
