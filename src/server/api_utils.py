import logging
import tempfile
from pathlib import Path

from fastapi import UploadFile

from core.utils import is_supported

logger = logging.getLogger(__name__)


def filter_supported_uploads(uploaded_files: list[UploadFile]) -> list[UploadFile]:
    validated_files: list[UploadFile] = []

    for file in uploaded_files:
        filename = file.filename or ""

        if is_supported(filename):
            validated_files.append(file)
        else:
            logger.warning("Unsupported file type: %s", filename)

    return validated_files


async def adapt_upload_files(upload_files: list[UploadFile]) -> list[Path]:
    paths = []
    seen_filenames = set()

    temp_dir = Path(tempfile.gettempdir())

    for file in upload_files:
        raw_filename = file.filename or "unknown"

        safe_name = Path(raw_filename).name
        p = Path(safe_name)
        stem = p.stem
        suffix = p.suffix.lower()

        unique_name = safe_name
        counter = 1
        target_path = temp_dir / unique_name

        while unique_name in seen_filenames or target_path.exists():
            unique_name = f"{stem} ({counter}){suffix}"
            target_path = temp_dir / unique_name
            counter += 1

        seen_filenames.add(unique_name)

        content = await file.read()
        target_path.write_bytes(content)

        paths.append(target_path)

    return paths
