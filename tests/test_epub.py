from unittest.mock import MagicMock

import pytest
from bs4 import BeautifulSoup

from parsers.epub import _extract_chapter_text, extract_epub_metadata


@pytest.fixture
def fake_book(tmp_path):
    return tmp_path / "book.epub"


@pytest.fixture
def mock_genai_client():
    client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is a generated response from artificial intelligence."

    client.models.generate_content.return_value = mock_response
    return client


def test_extract_epub_metadata_title():
    fake_epub = fake_book()
    fake_epub.write_bytes(b"fake data")
    book = MagicMock()
    book.get_metadata.return_value = [("My Book",)]
    book.spine = []
    book.get_items_of_type.return_value = []
    result = extract_epub_metadata(book, epub_path=fake_epub)

    assert result["title"] == "My Book"


def test_extract_epub_metadata():
    fake_epub = fake_book()
    fake_epub.write_bytes(b"fake data")
    book = MagicMock()
    book.get_metadata.return_value = []
    book.spine = []
    book.get_items_of_type.return_value = []
    result = extract_epub_metadata(book, epub_path=fake_epub)

    assert result["title"] == "Book"


def test_extract_chapter_text_decodes_bytes():
    item = MagicMock()
    item.get_content.return_value = b"<html><body><p>Hello world</p></body></html>"

    text, soup = _extract_chapter_text(item, image_descriptions={}, strip_nav=True)

    assert "Hello world" in text
    assert isinstance(soup, BeautifulSoup)


def test_extract_chapter_text_strips_nav():
    item = MagicMock()
    item.get_content.return_value = """
        <html>
            <body>
                <nav>Navigation menu</nav>
                <script>alert('test');</script>
                <p>Main content</p>
            </body>
        </html>
    """

    text, soup = _extract_chapter_text(item, image_descriptions={}, strip_nav=True)

    assert soup.find("nav") is None
    assert soup.find("script") is None
    assert "Navigation menu" not in text
    assert "Main content" in text


def test_extract_chapter_text_without_stripping_nav():
    item = MagicMock()
    item.get_content.return_value = "<html><body><nav>Keep this</nav></body></html>"
    _, soup = _extract_chapter_text(item, image_descriptions={}, strip_nav=False)

    assert soup.find("nav") is not None
