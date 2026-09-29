from pathlib import Path

import pytest

from cli.run_cli import _get_files_cli


def test_get_files_cli_valid_dir(tmp_path):
    file1 = tmp_path / "file1.txt"
    file1.write_text("content 1")
    file2 = tmp_path / "file2.txt"
    file2.write_text("content 2")
    files = _get_files_cli(tmp_path)
    assert set(files) == {file1, file2}
