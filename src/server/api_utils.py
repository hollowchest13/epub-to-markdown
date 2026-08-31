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


async def adapt_upload_files(upload_files: list[UploadFile]) -> list[tuple[Path, str]]:
    paths = []
    for file in upload_files:
        filename = file.filename or "unknown"
        suffix = Path(filename).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            paths.append((Path(tmp.name), Path(filename).stem))
    return paths
