# test_clean_markdown.py
from cleaner import clean_text
import pytest


def test_removes_xml_declaration():
    text = "<?xml version='1.0'?>\nHello world"
    assert clean_text(text) == "Hello world"


def test_removes_picture_text_comments():
    text = "<!-- Start of picture text -->\naQQ<br>\n<!-- End of picture text -->\nReal content"
    assert clean_text(text) == "Real content"


def test_removes_epub_links():
    text = "See chapter (c01.xhtml#section1) for details"
    assert clean_text(text) == "See chapter  for details"


def test_collapses_multiple_newlines():
    text = "Line 1\n\n\n\nLine 2"
    assert clean_text(text) == "Line 1\n\nLine 2"


def test_strips_whitespace():
    text = "  Hello world  "
    assert clean_text(text) == "Hello world"


@pytest.mark.parametrize(
    "html_input, expected_output",
    [
        ("<u></u>", ""),
        ("<p>Hello <b>World</b>!</p>", "Hello World!"),
        ('<a href="link">Link</a>', "Link"),
        ("Just text", "Just text"),
        ("<span><span>Nested</span> tags</span>", "Nested tags"),
    ],
)
def test_remove_html_tags(html_input, expected_output):
    assert clean_text(html_input) == expected_output
