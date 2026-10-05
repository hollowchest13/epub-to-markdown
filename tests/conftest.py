from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_config_manager() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock()
