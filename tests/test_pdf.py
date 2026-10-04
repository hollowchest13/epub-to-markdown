import io
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz
import pytest
from PIL import Image

from errors.api_errors import RateLimitExceeded
from parsers.pdf import PdfParser


@pytest.fixture
def mock_parser(mock_config_manager: MagicMock) -> PdfParser:
    return PdfParser(config_manager=mock_config_manager)


@pytest.fixture
def mock_pdf_file(tmp_path):
    """Creates a PDF file in the temporary directory (tmp_path) with 3 different page types:
    0 - text only
    1 - image only
    2 - text + image
    """
    doc = fitz.open()

    img = Image.new("RGB", (100, 100), color="green")
    img_io = io.BytesIO()
    img.save(img_io, format="PNG")
    img_bytes = img_io.getvalue()
    page0 = doc.new_page()
    page0.insert_text((50, 50), "This is a clean text document.", fontsize=14)
    page1 = doc.new_page()
    page1.insert_image(fitz.Rect(50, 50, 150, 150), stream=img_bytes)
    page2 = doc.new_page()
    page2.insert_text((50, 50), "Mixed content: text and image below.", fontsize=12)
    page2.insert_image(fitz.Rect(50, 80, 130, 160), stream=img_bytes)

    file_path = tmp_path / "test_document.pdf"
    doc.save(file_path)
    doc.close()
    return file_path


@pytest.fixture
def mock_doc(mock_pdf_file: Path) -> Iterator[fitz.Document]:
    doc = fitz.open(mock_pdf_file)
    yield doc
    doc.close()


@pytest.fixture
def mock_page():
    """A fixture for creating a mock page."""

    class MockPage:
        def __init__(self, text=""):
            self._text = text

        def get_text(self):
            return self._text

    return MockPage


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


def test_plan_to_bytes(mock_doc, mock_parser):
    plan = [
        ("local", [0]),
        ("gemini", [1]),
        ("gemini", [2]),
    ]

    result = mock_parser._plan_to_bytes(mock_doc, plan=plan)

    assert len(result) == 3

    method_0, bytes_0 = result[0]
    assert method_0 == "local"
    doc_0 = fitz.open("pdf", bytes_0)
    page_0: fitz.Page = doc_0[0]
    assert len(doc_0) == 1
    assert "clean text document" in page_0.get_text()
    assert len(doc_0[0].get_images()) == 0
    doc_0.close()

    method_1, bytes_1 = result[1]
    assert method_1 == "gemini"
    doc_1 = fitz.open("pdf", bytes_1)
    assert len(doc_1) == 1
    assert len(doc_1[0].get_images()) > 0
    doc_1.close()

    method_2, bytes_2 = result[2]
    assert method_2 == "gemini"
    doc_2 = fitz.open("pdf", bytes_2)
    assert len(doc_2) == 1
    assert "Mixed content" in doc_2[0].get_text()
    assert len(doc_2[0].get_images()) > 0
    doc_2.close()


def test_build_processing_plan(mock_doc, monkeypatch, mock_parser):

    assess_results = {0: False, 1: True, 2: False}
    monkeypatch.setattr(
        mock_parser, "_assess_page", lambda page: assess_results[page.number]
    )
    plan = mock_parser._build_processing_plan(mock_doc, max_pages_per_batch=1)
    expected_plan = [
        ("local", [0]),
        ("gemini", [1]),
        ("local", [2]),
    ]

    assert plan == expected_plan


def test_assess_page_all_false(mock_page, mock_parser, monkeypatch):
    """Scenario: standard page (lots of text, no formulas, no images) -> should return False."""

    page = mock_page("This is a very long normal text page " * 5)

    monkeypatch.setattr(
        mock_parser, "_has_significant_images", lambda p, size_ratio: False
    )

    result = mock_parser._assess_page(page)
    assert result is False


def test_assess_page_is_scanned(mock_page, mock_parser, monkeypatch):
    """Scenario: minimal text (scan) -> must return True (`is_scanned` triggers)."""
    page = mock_page("Short text")

    monkeypatch.setattr(
        mock_parser, "_has_significant_images", lambda p, size_ratio: False
    )

    result = mock_parser._assess_page(page)
    assert result is True


def test_assess_page_has_math(mock_page, mock_parser, monkeypatch):
    """Scenario: too many mathematical formulas -> should return True (has_math triggers)."""

    math_text = "Normal text " + " ± " * 6
    page = mock_page(math_text)

    monkeypatch.setattr(
        mock_parser, "_has_significant_images", lambda p, size_ratio: False
    )

    result = mock_parser._assess_page(page)
    assert result is True


def test_assess_page_has_images(mock_page, mock_parser, monkeypatch):
    """Scenario: there are significant images -> must return True (has_images triggers)."""
    page = mock_page("Normal text " * 10)

    monkeypatch.setattr(
        mock_parser, "_has_significant_images", lambda p, size_ratio: True
    )

    result = mock_parser._assess_page(page)
    assert result is True


def test_extract_pdf_metadata_full(mock_parser, mock_doc, mock_pdf_file):
    """Scenario: the document contains complete metadata -> all fields are correctly passed to build_metadata."""
    mock_doc.metadata = {
        "title": "Test Title",
        "author": "John Doe",
        "producer": "Test Producer",
        "creationDate": "D:20260101000000Z",
        "language": "en",
        "subject": "Test Subject",
        "keywords": "python, testing",
    }
    pdf_path = mock_pdf_file

    with (
        patch("parsers.pdf.build_metadata") as mock_build,
        patch("parsers.pdf.clean_filename") as mock_clean,
    ):
        mock_build.return_value = {"status": "success"}

        result = mock_parser._extract_pdf_metadata(doc=mock_doc, pdf_path=pdf_path)

        mock_build.assert_called_once()
        _, kwargs = mock_build.call_args

        assert kwargs["source_file"] == pdf_path
        extra = kwargs["extra"]
        assert extra["title"] == "Test Title"
        assert extra["author"] == ["John Doe"]
        assert extra["publisher"] == "Test Producer"
        assert extra["published_date"] == "D:20260101000000Z"
        assert extra["language"] == "en"
        assert extra["description"] == "Test Subject"
        assert extra["subjects"] == ["python, testing"]

        mock_clean.assert_not_called()
        assert result == {"status": "success"}


def test_extract_pdf_metadata_fallback(mock_parser, mock_doc, mock_pdf_file):
    """Scenario: metadata is missing -> fallbacks are triggered (clean_filename for title, etc.)."""
    mock_doc.metadata = {}
    pdf_path = mock_pdf_file

    with (
        patch("parsers.pdf.build_metadata") as mock_build,
        patch(
            "parsers.pdf.clean_filename", return_value="Clean Document Name"
        ) as mock_clean,
    ):
        mock_parser._extract_pdf_metadata(doc=mock_doc, pdf_path=pdf_path)

        mock_clean.assert_called_once_with(file_path=pdf_path)

        _, kwargs = mock_build.call_args
        extra = kwargs["extra"]
        assert extra["title"] == "Clean Document Name"
        assert extra["author"] == [None]
        assert extra["publisher"] is None
        assert extra["subjects"] == []


def test_get_chunk_text_gemini_success(mock_parser):
    """Scenario: Gemini method succeeds and returns text of sufficient length."""
    mock_client = MagicMock()
    mock_parser._min_chunk_lenght = 10

    with patch(
        "parsers.pdf.fetch_batch_with_retry",
        return_value="This is a long enough text from Gemini.",
    ) as mock_fetch:
        result = mock_parser._get_chunk_text(
            pdf_bytes=b"dummy_pdf_bytes",
            method="gemini",
            client=mock_client,
        )

        mock_fetch.assert_called_once()
        assert result == "This is a long enough text from Gemini."


def test_get_chunk_text_gemini_fallback_too_short(mock_parser):
    """Scenario: Gemini returns text that is too short -> should fall back to local OCR."""
    mock_client = MagicMock()
    mock_parser._min_chunk_lenght = 50

    with (
        patch("parsers.pdf.fetch_batch_with_retry", return_value="Short"),
        patch.object(
            mock_parser, "_local_conversion", return_value="Local OCR fallback text"
        ) as mock_local,
    ):
        result = mock_parser._get_chunk_text(
            pdf_bytes=b"dummy_pdf_bytes",
            method="gemini",
            client=mock_client,
        )

        mock_local.assert_called_once_with(pdf_bytes=b"dummy_pdf_bytes", force_ocr=True)
        assert result == "Local OCR fallback text"


def test_get_chunk_text_gemini_fallback_none(mock_parser, mock_client):
    """Scenario: Gemini returns None -> should fall back to local OCR."""

    with (
        patch("parsers.pdf.fetch_batch_with_retry", return_value=None),
        patch.object(
            mock_parser, "_local_conversion", return_value="Local OCR fallback text"
        ) as mock_local,
    ):
        result = mock_parser._get_chunk_text(
            pdf_bytes=b"dummy_pdf_bytes",
            method="gemini",
            client=mock_client,
        )

        mock_local.assert_called_once_with(pdf_bytes=b"dummy_pdf_bytes", force_ocr=True)
        assert result == "Local OCR fallback text"


def test_get_chunk_text_rate_limit_exception(mock_parser, mock_client):
    """Scenario: RateLimitExceeded is raised -> triggers callback and local OCR fallback."""
    mock_callback = MagicMock()

    with (
        patch(
            "parsers.pdf.fetch_batch_with_retry", side_effect=RateLimitExceeded("Limit")
        ),
        patch.object(
            mock_parser, "_local_conversion", return_value="Fallback after rate limit"
        ) as mock_local,
    ):
        result = mock_parser._get_chunk_text(
            pdf_bytes=b"dummy_pdf_bytes",
            method="gemini",
            client=mock_client,
            on_rate_limit=mock_callback,
        )

        mock_callback.assert_called_once()
        mock_local.assert_called_once_with(pdf_bytes=b"dummy_pdf_bytes", force_ocr=True)
        assert result == "Fallback after rate limit"


def test_get_chunk_text_general_exception(mock_parser, mock_client):
    """Scenario: Unexpected exception from Gemini API -> logs error and falls back to local OCR."""

    with (
        patch("parsers.pdf.fetch_batch_with_retry", side_effect=Exception("API Error")),
        patch.object(
            mock_parser, "_local_conversion", return_value="Fallback after error"
        ) as mock_local,
    ):
        result = mock_parser._get_chunk_text(
            pdf_bytes=b"dummy_pdf_bytes",
            method="gemini",
            client=mock_client,
        )

        mock_local.assert_called_once_with(pdf_bytes=b"dummy_pdf_bytes", force_ocr=True)
        assert result == "Fallback after error"


def test_get_chunk_text_local_method(mock_parser):
    """Scenario: Method is 'local' -> directly invokes local conversion without force_ocr."""
    with patch.object(
        mock_parser, "_local_conversion", return_value="Pure local text"
    ) as mock_local:
        result = mock_parser._get_chunk_text(
            pdf_bytes=b"dummy_pdf_bytes",
            method="local",
            client=None,
        )

        mock_local.assert_called_once_with(pdf_bytes=b"dummy_pdf_bytes")
        assert result == "Pure local text"


def test_local_conversion_success(mock_parser, mock_pdf_file):
    """Сценарій: успішна локальна конвертація у markdown."""
    pdf_bytes = mock_pdf_file.read_bytes()

    with patch(
        "parsers.pdf.pymupdf4llm.to_markdown", return_value="# Mocked Markdown Content"
    ) as mock_to_md:
        result = mock_parser._local_conversion(pdf_bytes=pdf_bytes, force_ocr=False)

        mock_to_md.assert_called_once()
        _, kwargs = mock_to_md.call_args
        assert kwargs.get("force_ocr") is False or mock_to_md.call_args[0][1] is False
        assert result == "# Mocked Markdown Content"


def test_local_conversion_force_ocr(mock_parser):
    """Scenario: verify that the force_ocr=True flag is passed to pymupdf4llm."""
    with fitz.open() as doc:
        doc.new_page()
        pdf_bytes = doc.tobytes()

    with patch(
        "parsers.pdf.pymupdf4llm.to_markdown", return_value="OCR text"
    ) as mock_to_md:
        result = mock_parser._local_conversion(pdf_bytes=pdf_bytes, force_ocr=True)

        _, kwargs = mock_to_md.call_args
        assert kwargs["force_ocr"] is True
        assert result == "OCR text"


def test_local_conversion_type_error(mock_parser):
    """Scenario: pymupdf4llm returns a non-string type -> expect a TypeError."""
    with fitz.open() as doc:
        doc.new_page()
        pdf_bytes = doc.tobytes()

    with (
        patch("parsers.pdf.pymupdf4llm.to_markdown", return_value={"invalid": "type"}),
        pytest.raises(TypeError, match="Expected str, got"),
    ):
        mock_parser._local_conversion(pdf_bytes=pdf_bytes)
