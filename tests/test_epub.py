from unittest.mock import MagicMock

import pytest
from bs4 import BeautifulSoup

from parsers.epub import EpubParser


@pytest.fixture
def mock_config_manager() -> MagicMock:
    return MagicMock()


@pytest.fixture
def epub_parser(mock_config_manager: MagicMock) -> EpubParser:
    return EpubParser(config_manager=mock_config_manager)


def test_get_epub_images(epub_parser):
    mock_book = MagicMock()
    mock_item_1 = MagicMock()
    mock_item_1.get_name.return_value = "images/cover.jpg"
    mock_item_1.get_content.return_value = b"fake_image_bytes_1"

    mock_item_2 = MagicMock()
    mock_item_2.get_name.return_value = "images/logo.png"
    mock_item_2.get_content.return_value = b"fake_image_bytes_2"
    mock_book.get_items_of_type.return_value = [mock_item_1, mock_item_2]
    parser = epub_parser
    images = parser._get_epub_images(book=mock_book)
    assert len(images) == 2
    assert images["images/cover.jpg"] == b"fake_image_bytes_1"
    assert images["images/logo.png"] == b"fake_image_bytes_2"


def test_replace_images(epub_parser):
    html_content = """
    <html>
        <body>
            <p>Some text before</p>
            <img src="images/cover.jpg"/>
            <img src="unknown.png"/>
            <p>Some text after</p>
        </body>
    </html>
    """
    soup = BeautifulSoup(html_content, "html.parser")
    image_descriptions = {
        "images/cover.jpg": "Description of the cover image.",
    }

    parser = epub_parser
    updated_soup = parser._replace_images(
        soup=soup, image_descriptions=image_descriptions
    )

    paragraphs = updated_soup.find_all("p")
    assert any("Description of the cover image." in p.text for p in paragraphs)
    assert updated_soup.find("img", src="images/cover.jpg") is None
    assert updated_soup.find("img", src="unknown.png") is not None
