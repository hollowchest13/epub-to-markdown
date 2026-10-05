import io
from unittest.mock import patch

import pytest
from fastapi import UploadFile

from server.api_utils import adapt_upload_files, filter_supported_uploads

# Assuming your functions are imported from your module:
# from server.api_utils import filter_supported_uploads, adapt_upload_files


# --- Tests for filter_supported_uploads ---


def test_filter_supported_uploads_mixed():
    """Verify that only supported files are kept and unsupported ones are logged/filtered out."""
    # 1. Create mock UploadFiles with different names
    file1 = UploadFile(filename="book.epub", file=io.BytesIO(b"data"))
    file2 = UploadFile(filename="document.pdf", file=io.BytesIO(b"data"))
    file3 = UploadFile(filename="archive.zip", file=io.BytesIO(b"data"))

    # 2. Mock is_supported to return True for epub, False for others
    with patch("server.api_utils.is_supported") as mock_is_supported:
        mock_is_supported.side_effect = lambda name: name.endswith(".epub")

        result = filter_supported_uploads([file1, file2, file3])

        # 3. Assertions
        assert len(result) == 1
        assert result[0].filename == "book.epub"


def test_filter_supported_uploads_empty_filename():
    """Verify handling of files with None or empty filenames."""
    file_no_name = UploadFile(filename=None, file=io.BytesIO(b"data"))

    with patch("server.api_utils.is_supported", return_value=False):
        result = filter_supported_uploads([file_no_name])
        assert len(result) == 0


# --- Tests for adapt_upload_files ---


@pytest.mark.anyio
async def test_adapt_upload_files_success(tmp_path):
    """Verify that upload files are correctly written to disk and paths are returned."""
    file1 = UploadFile(filename="book1.epub", file=io.BytesIO(b"content 1"))
    file2 = UploadFile(filename="book2.epub", file=io.BytesIO(b"content 2"))

    # Redirect tempfile.gettempdir() to pytest's tmp_path for isolation
    with patch("tempfile.gettempdir", return_value=str(tmp_path)):
        paths = await adapt_upload_files([file1, file2])

        assert len(paths) == 2

        # Check file 1
        assert paths[0].exists()
        assert paths[0].name == "book1.epub"
        assert paths[0].read_bytes() == b"content 1"

        # Check file 2
        assert paths[1].exists()
        assert paths[1].name == "book2.epub"
        assert paths[1].read_bytes() == b"content 2"


@pytest.mark.anyio
async def test_adapt_upload_files_name_collision(tmp_path):
    """Verify that duplicate filenames automatically get a unique suffix (counter)."""
    # Uploading two files with the exact same name
    file1 = UploadFile(filename="guide.epub", file=io.BytesIO(b"first"))
    file2 = UploadFile(filename="guide.epub", file=io.BytesIO(b"second"))

    with patch("tempfile.gettempdir", return_value=str(tmp_path)):
        paths = await adapt_upload_files([file1, file2])

        assert len(paths) == 2

        # First file should keep original name
        assert paths[0].name == "guide.epub"
        assert paths[0].read_bytes() == b"first"

        # Second file should get a uniqueness suffix
        assert paths[1].name == "guide (1).epub"
        assert paths[1].read_bytes() == b"second"
