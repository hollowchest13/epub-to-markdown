from unittest.mock import MagicMock, patch

import ebooklib
import pytest
from bs4 import BeautifulSoup

from parsers.epub import EpubParser


@pytest.fixture
def mock_parser(mock_config_manager: MagicMock) -> EpubParser:
    return EpubParser(config_manager=mock_config_manager)


@pytest.fixture
def mock_book():
    book = MagicMock()
    book.title = "Test Book"

    item_1 = MagicMock()
    item_1.get_type.return_value = ebooklib.ITEM_DOCUMENT
    item_1.get_content.return_value = (
        b"<html><body>Hello world from test book!</body></html>"
    )

    item_2 = MagicMock()
    item_2.get_type.return_value = ebooklib.ITEM_DOCUMENT
    item_2.get_content.return_value = (
        b"<html><body>Second chapter content here.</body></html>"
    )

    book.spine = [("item_1", "yes"), ("item_2", "yes")]
    book.get_item_with_id.side_effect = lambda item_id: {
        "item_1": item_1,
        "item_2": item_2,
    }.get(item_id)
    book.get_items_of_type.return_value = [item_1, item_2]

    return book


def test_get_epub_images(mock_parser, mock_book):
    mock_item_1 = MagicMock()
    mock_item_1.get_name.return_value = "images/cover.jpg"
    mock_item_1.get_content.return_value = b"fake_image_bytes_1"

    mock_item_2 = MagicMock()
    mock_item_2.get_name.return_value = "images/logo.png"
    mock_item_2.get_content.return_value = b"fake_image_bytes_2"
    mock_book.get_items_of_type.return_value = [mock_item_1, mock_item_2]
    parser = mock_parser
    images = parser._get_epub_images(book=mock_book)
    assert len(images) == 2
    assert images["images/cover.jpg"] == b"fake_image_bytes_1"
    assert images["images/logo.png"] == b"fake_image_bytes_2"


def test_replace_images(mock_parser):
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

    parser = mock_parser
    updated_soup = parser._replace_images(
        soup=soup, image_descriptions=image_descriptions
    )

    paragraphs = updated_soup.find_all("p")
    assert any("Description of the cover image." in p.text for p in paragraphs)
    assert updated_soup.find("img", src="images/cover.jpg") is None
    assert updated_soup.find("img", src="unknown.png") is not None


def test_fallback_collect_epub_chapters(mock_client, mock_parser, mock_book):
    with patch("core.utils.images_to_md") as mock_images_to_md:
        mock_images_to_md.return_value = {"image_1": "image_desc_1"}
        mock_parser._get_epub_images = MagicMock(return_value={"image_1": b"bytes"})
        mock_parser._chapter_min_size = 1000

        mock_soup = MagicMock()
        mock_parser._extract_chapter_text = MagicMock(
            return_value=("Short fallback text", mock_soup)
        )

        chapters = mock_parser._collect_epub_chapters(
            book=mock_book, client=mock_client
        )

        assert len(chapters) == 1
        assert chapters[0][0] == "Full content"
        assert "Short fallback text" in chapters[0][1]


def test_collect_epub_chapters(mock_client, mock_parser, mock_book):
    with patch("core.utils.images_to_md") as mock_images_to_md:
        mock_images_to_md.return_value = {"image_1": "image_desc_1"}
        mock_parser._get_epub_images = MagicMock(return_value={"image_1": b"bytes"})
        mock_parser._chapter_min_size = 5

        mock_soup_1 = MagicMock()
        mock_soup_1.find.return_value.get_text.return_value = "Chapter 1"

        mock_soup_2 = MagicMock()
        mock_soup_2.find.return_value.get_text.return_value = "Chapter 2"

        mock_parser._extract_chapter_text = MagicMock(
            side_effect=[
                ("Text for chapter one...", mock_soup_1),
                ("Text for chapter two...", mock_soup_2),
            ]
        )

        chapters = mock_parser._collect_epub_chapters(
            book=mock_book, client=mock_client
        )

        assert len(chapters) == 2
        assert chapters[0] == ("Chapter 1", "Text for chapter one...")
        assert chapters[1] == ("Chapter 2", "Text for chapter two...")


def test_extract_epub_metadata(mock_parser, mock_book, tmp_path):
    fake_epub_file = tmp_path / "test_book.epub"
    fake_epub_file.touch()

    def mock_get_metadata(namespace, key):
        metadata_store = {
            "title": [("Test Book Title", "lang")],
            "creator": [("John Doe", "lang")],
            "publisher": ["Test Publisher"],
        }
        return metadata_store.get(key, [])

    mock_book.get_metadata.side_effect = mock_get_metadata

    result = mock_parser._extract_epub_metadata(mock_book, epub_path=fake_epub_file)

    assert result["title"] == "Test Book Title"
    assert result["total_spine_items"] == 2
    assert result["estimated_total_words"] == 9
