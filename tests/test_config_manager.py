import os
from unittest.mock import MagicMock, patch

import pytest
from google.genai.errors import APIError

from config.config_manager import ConfigManager
from errors.network_errors import NetworkError


@pytest.fixture
def config_manager(tmp_path):
    """Creates an actual instance of ConfigManager with an isolated temporary directory."""
    return ConfigManager(base_dir=tmp_path)


def test_default_settings_and_directories(config_manager):
    """Verify default settings and mandatory directories creation."""

    assert config_manager.model == "gemini-3.1-flash-lite"
    assert config_manager.img_chunk_size == 15
    assert config_manager.api_delay == 6
    assert config_manager.mode == "api"

    out_dir = config_manager.output_dir
    uploads_dir = config_manager.uploads_dir

    assert out_dir.exists()
    assert out_dir.is_dir()
    assert uploads_dir.exists()
    assert uploads_dir.is_dir()


def test_toml_data_missing(config_manager):
    """Verify behavior when pyproject.toml is missing."""

    data = config_manager.toml_data
    assert data == {}


def test_toml_data_valid(config_manager):
    """Verify reading of a valid pyproject.toml file."""
    toml_file = config_manager._base_dir / "pyproject.toml"
    toml_file.write_text('[project]\nname = "test-project"\n')

    data = config_manager.toml_data
    assert data == {"project": {"name": "test-project"}}


def test_toml_data_invalid(config_manager):
    """Verify safe handling of TOML syntax errors."""
    toml_file = config_manager._base_dir / "pyproject.toml"
    toml_file.write_text("invalid toml syntax content [")

    data = config_manager.toml_data
    assert data == {}


def test_api_key_management(config_manager):
    """Verify saving, reading, and activation of the API key."""

    assert config_manager.get_api_key() is None

    test_key = "AIzaSyTestKey123456"
    config_manager.save_and_activate(test_key)

    assert os.environ.get("GEMINI_API_KEY") == test_key

    new_manager = ConfigManager(base_dir=config_manager._base_dir)
    assert new_manager.get_api_key() == test_key


@patch("config.config_manager.genai.Client")
def test_validate_key_success(mock_client_cls, config_manager):
    """Verify successful API key validation via Google GenAI."""
    mock_client_instance = mock_client_cls.return_value
    mock_client_instance.models.generate_content.return_value = MagicMock()

    valid_key = "AIzaSyValidKey"
    result = config_manager.validate_key(valid_key)

    assert result == valid_key
    mock_client_instance.models.generate_content.assert_called_once_with(
        model=config_manager.model,
        contents="Test",
    )


@patch("config.config_manager.genai.Client")
def test_validate_key_invalid_api_error(mock_client_cls, config_manager):
    """Verify handling of invalid key (APIError)."""
    mock_client_instance = mock_client_cls.return_value

    api_err = APIError(code=401, response_json=None)
    mock_client_instance.models.generate_content.side_effect = api_err

    with pytest.raises(ValueError, match="Invalid API key"):
        config_manager.validate_key("AIzaSyInvalidKey")


@patch("config.config_manager.genai.Client")
def test_validate_key_network_error(mock_client_cls, config_manager):
    """Verify handling of network issues during validation."""
    mock_client_instance = mock_client_cls.return_value

    mock_client_instance.models.generate_content.side_effect = ConnectionError(
        "No internet"
    )

    with pytest.raises(NetworkError, match="Internet connection error"):
        config_manager.validate_key("AIzaSySomeKey")
