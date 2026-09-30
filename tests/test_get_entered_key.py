from unittest.mock import MagicMock

import pytest

from cli.run_cli import _get_entered_key


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
