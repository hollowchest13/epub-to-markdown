from unittest.mock import MagicMock

import pytest

from parsers.pdf import PdfParser


@pytest.fixture
def mock_parser(mock_config_manager: MagicMock) -> PdfParser:
    return PdfParser(config_manager=mock_config_manager)


def test_has_significant_images_scenarios(mock_parser):
    """Test various scenarios for significant images detection on a page."""

    mock_page = MagicMock()
    mock_page.rect.width = 100
    mock_page.rect.height = 100

    mock_page.get_image_info.return_value = [{"bbox": [0, 0, 40, 50]}]
    assert mock_parser._has_significant_images(mock_page, size_ratio=0.05) is True

    mock_page.get_image_info.return_value = [{"bbox": [0, 0, 10, 10]}]
    assert mock_parser._has_significant_images(mock_page, size_ratio=0.05) is False

    mock_page.get_image_info.return_value = []
    assert mock_parser._has_significant_images(mock_page, size_ratio=0.05) is False

    mock_page.get_image_info.return_value = [{}]
    assert mock_parser._has_significant_images(mock_page, size_ratio=0.05) is False
