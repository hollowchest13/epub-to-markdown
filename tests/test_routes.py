import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.routes import (
    _cleanup_temp_files,
    _create_result_archive,
    _file_stream_generator,
    router,
)


@pytest.fixture
def mock_app():
    """Create a FastAPI app instance with mocked state and included router."""
    app = FastAPI()

    # Mock config_manager and store it in app.state
    mock_config_manager = MagicMock()
    mock_config_manager.output_dir = Path("/tmp")
    app.state.config_manager = mock_config_manager

    app.include_router(router)
    return app


@pytest.fixture
def client(mock_app):
    return TestClient(mock_app)


def test_cleanup_temp_files_success(tmp_path):
    """Verify successful deletion of existing temporary files and directory."""
    file1 = tmp_path / "temp1.txt"
    file2 = tmp_path / "temp2.txt"
    file1.write_text("data 1")
    file2.write_text("data 2")

    request_dir = tmp_path / "request_123"
    request_dir.mkdir()
    sub_file = request_dir / "output.pdf"
    sub_file.write_text("some content")

    assert file1.exists()
    assert file2.exists()
    assert request_dir.exists()
    assert sub_file.exists()

    _cleanup_temp_files([file1, file2], request_dir)

    assert not file1.exists()
    assert not file2.exists()
    assert not request_dir.exists()
    assert not sub_file.exists()


def test_cleanup_temp_files_graceful_handling(tmp_path):
    """Ensure the function does not crash if files or directory are already missing."""
    non_existent_file = tmp_path / "ghost.txt"
    non_existent_dir = tmp_path / "non_existent_folder"
    _cleanup_temp_files([non_existent_file], non_existent_dir)


def test_create_result_archive_success(tmp_path):
    """Verify that result archive correctly packages .md files maintaining directory structure."""
    request_dir = tmp_path / "request_001"
    request_dir.mkdir()

    tmp_path1 = tmp_path / "doc1.txt"
    tmp_path2 = tmp_path / "doc2.txt"
    tmp_paths = [tmp_path1, tmp_path2]

    result_dir1 = request_dir / tmp_path1.stem
    result_dir1.mkdir()
    md_file1 = result_dir1 / "chapter1.md"
    md_file1.write_text("# Chapter 1 content")

    result_dir2 = request_dir / tmp_path2.stem
    result_dir2.mkdir()
    sub_dir = result_dir2 / "nested"
    sub_dir.mkdir()
    md_file2 = sub_dir / "chapter2.md"
    md_file2.write_text("# Chapter 2 nested content")

    txt_file = result_dir1 / "notes.txt"
    txt_file.write_text("should be ignored")

    zip_path = _create_result_archive(request_dir, tmp_paths)

    assert zip_path.exists()
    assert zip_path.name == "converted.zip"

    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        assert "doc1/chapter1.md" in namelist
        assert "doc2/nested/chapter2.md" in namelist
        assert "doc1/notes.txt" not in namelist


def test_create_result_archive_missing_result_dirs(tmp_path):
    """Ensure archive creation handles non-existent result directories gracefully."""
    request_dir = tmp_path / "request_002"
    request_dir.mkdir()

    missing_tmp_path = tmp_path / "missing.txt"

    zip_path = _create_result_archive(request_dir, [missing_tmp_path])

    assert zip_path.exists()
    with zipfile.ZipFile(zip_path, "r") as zf:
        assert len(zf.namelist()) == 0


def test_file_stream_generator(tmp_path):
    """Verify that generator yields file chunks and performs cleanup afterwards."""
    request_dir = tmp_path / "request_stream"
    request_dir.mkdir()

    zip_path = request_dir / "converted.zip"
    sample_data = b"Hello, FastAPI stream! " * 500
    zip_path.write_bytes(sample_data)

    tmp_file = tmp_path / "temp_to_delete.txt"
    tmp_file.write_text("temporary data")

    assert zip_path.exists()
    assert tmp_file.exists()
    assert request_dir.exists()

    chunks = list(_file_stream_generator(zip_path, [tmp_file], request_dir))

    assert len(chunks) > 0
    assert b"".join(chunks) == sample_data

    assert not tmp_file.exists()
    assert not request_dir.exists()


def test_convert_success(client, mock_app, tmp_path):
    """Verify successful file conversion and zip streaming response."""
    mock_config = mock_app.state.config_manager
    mock_config.output_dir = tmp_path

    with (
        patch("server.routes.filter_supported_uploads") as mock_filter,
        patch("server.routes.adapt_upload_files") as mock_adapt,
        patch("server.routes._run_conversion"),
        patch("server.routes._create_result_archive") as mock_create_archive,
        patch("server.routes._file_stream_generator") as mock_stream_gen,
    ):
        dummy_file = MagicMock()
        mock_filter.return_value = [dummy_file]
        mock_adapt.return_value = [tmp_path / "adapted.epub"]

        dummy_zip = tmp_path / "converted.zip"
        dummy_zip.write_bytes(b"PK\x03\x04mock_zip_content")
        mock_create_archive.return_value = dummy_zip

        mock_stream_gen.return_value = iter([b"mock_chunk"])

        response = client.post(
            "/convert",
            files={"files": ("test.epub", b"epub content", "application/epub+zip")},
            headers={"x-api-key": "valid_key"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert (
            "attachment; filename=converted.zip"
            in response.headers["content-disposition"]
        )
        assert response.content == b"mock_chunk"


def test_convert_no_files(client):
    """Verify 422 validation error when no files are provided."""
    response = client.post("/convert", files={}, headers={"x-api-key": "valid_key"})
    assert response.status_code == 422


def test_convert_invalid_api_key(client, mock_app):
    """Verify 401 error when validate_key raises ValueError."""
    mock_config = mock_app.state.config_manager
    mock_config.validate_key.side_effect = ValueError("Invalid key")

    with patch("server.routes.filter_supported_uploads") as mock_filter:
        mock_filter.return_value = [MagicMock()]

        response = client.post(
            "/convert",
            files={"files": ("test.epub", b"content", "application/epub+zip")},
            headers={"x-api-key": "bad_key"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid Gemini API key"
