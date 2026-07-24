from unittest.mock import MagicMock
from parsers.epub import extract_epub_metadata


def test_extract_epub_metadata_title(tmp_path):
    fake_epub = tmp_path / "book.epub"
    fake_epub.write_bytes(b"fake data")
    book = MagicMock()
    book.get_metadata.return_value = [("My Book",)]
    book.spine = []
    book.get_items_of_type.return_value = []
    result = extract_epub_metadata(book, epub_path=fake_epub)

    assert result["title"] == "My Book"


def test_extract_epub_metadata(tmp_path):
    fake_epub = tmp_path / "book.epub"
    fake_epub.write_bytes(b"fake data")
    book = MagicMock()
    book.get_metadata.return_value = []
    book.spine = []
    book.get_items_of_type.return_value = []
    result = extract_epub_metadata(book, epub_path=fake_epub)

    assert result["title"] == "Book"
