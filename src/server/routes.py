import asyncio
import io
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from google import genai

from core.converter import convert_to_md
from server.api_utils import adapt_upload_files, filter_supported_uploads

router = APIRouter()


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
    tmp_paths_with_names = await adapt_upload_files(supported)
    tmp_paths = [p for p, _ in tmp_paths_with_names]
    loop = asyncio.get_running_loop()
    client = genai.Client(api_key=x_api_key)
    request_dir = config_manager.output_dir / str(uuid.uuid4())
    request_dir.mkdir(parents=True, exist_ok=True)
    try:
        await loop.run_in_executor(
            None,
            lambda: convert_to_md(
                files=tmp_paths,
                client=client,
                target_dir=request_dir,
                prompt_dict=config_manager.get_prompt_dict(),
                model=config_manager.model,
            ),
        )
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for tmp_path, original_stem in tmp_paths_with_names:
                result_dir = request_dir / tmp_path.stem
                if result_dir.exists():
                    for md_file in result_dir.rglob("*.md"):
                        base_name = Path(original_stem).stem or "document"
                        safe_name = Path(base_name).name
                        unique_suffix = tmp_path.stem
                        folder_name = f"{safe_name}_{unique_suffix}"
                        arc_path = Path(folder_name) / md_file.relative_to(result_dir)
                        zf.write(md_file, arc_path)
        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=converted.zip"},
        )
    finally:
        for path in tmp_paths:
            path.unlink(missing_ok=True)
        shutil.rmtree(request_dir, ignore_errors=True)


@router.get("/health")
async def health():
    return {"status": "ok"}
