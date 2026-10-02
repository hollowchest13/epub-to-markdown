from unittest.mock import MagicMock

import pytest

from cli.run_cli import _get_entered_key, _get_files_cli


def test_get_entered_key_quit(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "q")
    with pytest.raises(SystemExit, match="stopped by the user"):
        _get_entered_key(validator=lambda x: x)


def test_get_entered_key(monkeypatch):
    inputs = iter(["", "my_secret_key"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    mock_validator = MagicMock(side_effect=lambda key: key.upper())
    result = _get_entered_key(mock_validator)
    assert result == "MY_SECRET_KEY"
    mock_validator.assert_called_once_with("my_secret_key")


def test_get_entered_key_retries_on_value_error(monkeypatch):
    inputs = iter(["bad_key", "AIzaSyFakeKey"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    mock_validator = MagicMock(
        side_effect=[ValueError("Invalid format!"), "AIZASYFAKEKEY"]
    )
    result = _get_entered_key(mock_validator)
    assert result == "AIZASYFAKEKEY"
    assert mock_validator.call_count == 2


def test_get_files_cli_valid_dir(tmp_path):
    file1 = tmp_path / "file1.txt"
    file1.write_text("content 1")
    file2 = tmp_path / "file2.txt"
    file2.write_text("content 2")
    files = _get_files_cli(tmp_path)
    assert set(files) == {file1, file2}


def test_get_files_cli_not_a_dir(tmp_path):
    fake_dir = tmp_path / "not_a_dir.txt"
    fake_dir.write_text("I am a file")
    with pytest.raises(SystemExit, match="is not a valid directory."):
        _get_files_cli(fake_dir)


def test_get_files_cli_dir_is_empty(tmp_path):
    with pytest.raises(SystemExit, match="is empty"):
        _get_files_cli(tmp_path)
