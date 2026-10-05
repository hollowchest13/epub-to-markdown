from unittest.mock import MagicMock, patch

import pytest
from google.genai.errors import ClientError

from core.models import ImageAnalysisResponse
from core.utils import (
    call_gemini_api,
    collect_chapters_from_text,
    fetch_batch_with_retry,
    filter_supported_files,
    get_file_hash,
    images_to_md,
    is_supported,
)
from errors import RateLimitExceeded


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("f1.txt", False),
        ("f2.epub", True),
        ("f3.pdf", True),
        ("f4.md", True),
    ],
)
def test_is_supported(tmp_path, filename, expected):
    file_path = tmp_path / filename
    assert is_supported(file_path) == expected


def test_filter_supported_files(tmp_path):

    file_epub = tmp_path / "book.epub"
    file_png = tmp_path / "image.png"
    file_pdf = tmp_path / "report.pdf"
    file_txt = tmp_path / "notes.txt"
    input_files = [file_epub, file_png, file_pdf, file_txt]
    result = filter_supported_files(input_files)
    assert result == [file_epub, file_pdf]


def test_filter_supported_files_logging(tmp_path, caplog):
    file_png = tmp_path / "image.png"
    filter_supported_files([file_png])

    assert "Skipping unsupported file" in caplog.text
    assert "image.png" in caplog.text


@patch("core.utils.call_gemini_api")
@patch("time.sleep")
def test_fetch_batch_success(mock_sleep, mock_call_api):
    """Тест на успішне виконання з першої спроби (очікуємо JSON-список)."""
    mock_call_api.return_value = ["item1", "item2"]
    client = MagicMock()

    result = fetch_batch_with_retry(
        client=client,
        model="gemini-pro",
        contents=["test content"],
        max_api_retries=3,
        api_delay=1,
        expect_json=True,
        batch_size=2,
        batch_index=1,
    )

    assert result == ["item1", "item2"]
    mock_call_api.assert_called_once()
    mock_sleep.assert_not_called()  # Спати не довелося


@patch("core.utils.call_gemini_api")
@patch("time.sleep")
def test_fetch_batch_rate_limit_retry(mock_sleep, mock_call_api):
    """Retry test for RateLimitExceeded: error on the first attempt, success on the second."""
    mock_call_api.side_effect = [
        RateLimitExceeded("Rate limit hit"),
        ["item1", "item2"],
    ]
    client = MagicMock()

    result = fetch_batch_with_retry(
        client=client,
        model="gemini-pro",
        contents=["test content"],
        max_api_retries=3,
        api_delay=1,
        expect_json=True,
        batch_size=2,
        batch_index=1,
    )

    assert result == ["item1", "item2"]
    assert mock_call_api.call_count == 2
    mock_sleep.assert_called_once_with(5)


@patch("core.utils.call_gemini_api")
@patch("time.sleep")
def test_fetch_batch_client_error_400_aborts(mock_sleep, mock_call_api):
    """A test verifying that a 400 (Bad Request) error immediately throws an exception and does not perform retries."""

    err = ClientError(code=400, response_json={"error": "Bad Request"})

    mock_call_api.side_effect = err
    client = MagicMock()

    with pytest.raises(ClientError):
        fetch_batch_with_retry(
            client=client,
            model="gemini-pro",
            contents=["test content"],
            max_api_retries=3,
            api_delay=1,
            expect_json=True,
            batch_index=1,
        )

    mock_call_api.assert_called_once()
    mock_sleep.assert_not_called()


@patch("core.utils.call_gemini_api")
@patch("time.sleep")
def test_fetch_batch_validation_mismatch_retries(mock_sleep, mock_call_api):
    """A test for the case where the API returned the wrong data type (expected a list, got a string)."""
    mock_call_api.side_effect = ["invalid string response", ["item1", "item2"]]
    client = MagicMock()

    result = fetch_batch_with_retry(
        client=client,
        model="gemini-pro",
        contents=["test content"],
        max_api_retries=3,
        api_delay=2,
        expect_json=True,
        batch_size=2,
        batch_index=1,
    )

    assert result == ["item1", "item2"]
    assert mock_call_api.call_count == 2
    mock_sleep.assert_called_once_with(2)


@patch("core.utils.types")
def test_call_gemini_api_text_success(mock_types):
    """Test for the successful receipt of a standard text result (expect_json=False)."""
    client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Hello from Gemini"
    client.models.generate_content.return_value = mock_response

    result = call_gemini_api(
        client=client,
        model="gemini-pro",
        contents=["test prompt"],
        expect_json=False,
    )

    assert result == "Hello from Gemini"
    client.models.generate_content.assert_called_once()


@patch("core.utils.types")
def test_call_gemini_api_json_success(mock_types):
    """Test for the successful receipt of a structured JSON result (expect_json=True)."""
    client = MagicMock()
    mock_response = MagicMock()

    # Імітуємо правильний розпарсений об'єкт
    parsed_obj = MagicMock(spec=ImageAnalysisResponse)
    parsed_obj.results = ["item1", "item2"]
    mock_response.parsed = parsed_obj

    client.models.generate_content.return_value = mock_response

    result = call_gemini_api(
        client=client,
        model="gemini-pro",
        contents=["test image"],
        expect_json=True,
    )

    assert result == ["item1", "item2"]


@patch("core.utils.types")
def test_call_gemini_api_json_type_error(mock_types):
    """Test for a TypeError when a JSON schema was expected but the wrong data type was received in `parsed`."""
    client = MagicMock()
    mock_response = MagicMock()
    mock_response.parsed = "unexpected string instead of object"
    client.models.generate_content.return_value = mock_response

    with pytest.raises(TypeError, match="Expected ImageAnalysisResponse"):
        call_gemini_api(
            client=client,
            model="gemini-pro",
            contents=["test image"],
            expect_json=True,
        )


@patch("core.utils.types")
def test_call_gemini_api_client_error_400(mock_types):
    """Test for re-throwing ClientError on a 400 code."""
    client = MagicMock()
    err = ClientError(code=400, response_json={})
    client.models.generate_content.side_effect = err

    with pytest.raises(ClientError) as exc_info:
        call_gemini_api(
            client=client,
            model="gemini-pro",
            contents=["test"],
        )
    assert exc_info.value.code == 400


@patch("core.utils.types")
def test_call_gemini_api_client_error_429(mock_types):
    """Test for converting a ClientError with code 429 into a RateLimitExceeded exception."""
    client = MagicMock()
    err = ClientError(code=429, response_json={})
    client.models.generate_content.side_effect = err

    with pytest.raises(RateLimitExceeded):
        call_gemini_api(
            client=client,
            model="gemini-pro",
            contents=["test"],
        )


@patch("core.utils.types")
def test_call_gemini_api_client_error_503(mock_types):
    """Test for re-raising ClientError on 503 status code."""
    client = MagicMock()
    err = ClientError(code=503, response_json={})
    client.models.generate_content.side_effect = err

    with pytest.raises(ClientError) as exc_info:
        call_gemini_api(
            client=client,
            model="gemini-pro",
            contents=["test"],
        )
    assert exc_info.value.code == 503


def test_collect_chapters_with_intro_and_headers():
    """Test correct splitting of text with an introduction and multiple headers."""
    text = (
        "This is an introduction text that is definitely long enough to pass.\n\n"
        "# Chapter One\n"
        "Content of the first chapter goes here and it is quite detailed.\n\n"
        "## Chapter Two\n"
        "Content of the second chapter with some more text."
    )
    chapters = collect_chapters_from_text(text=text, chapter_min_size=10)

    assert len(chapters) == 3
    assert chapters[0][0] == "Introduction"
    assert chapters[1][0] == "Chapter One"
    assert chapters[2][0] == "Chapter Two"


def test_collect_chapters_filters_small_sections():
    """Test filtering out the introduction and sections smaller than chapter_min_size."""
    text = (
        "Tiny intro.\n\n"
        "# Chapter 1\n"
        "Short.\n\n"
        "## Chapter 2\n"
        "This chapter is actually quite long and should successfully pass the minimum size threshold filter."
    )
    chapters = collect_chapters_from_text(text=text, chapter_min_size=20)
    assert len(chapters) == 1
    assert chapters[0][0] == "Chapter 2"


def test_collect_chapters_no_headers_fallback():
    """Test text without headers but longer than chapter_min_size (returns Full Content)."""
    text = "This is a plain text without any markdown headers at all, but it is long enough."

    chapters = collect_chapters_from_text(text=text, chapter_min_size=10)

    assert len(chapters) == 1
    assert chapters[0][0] == "Full Content"
    assert chapters[0][1] == text


def test_collect_chapters_too_short_empty():
    """Test a text that is too short and has no headers (should return an empty list)."""
    text = "Short text."

    chapters = collect_chapters_from_text(text=text, chapter_min_size=100)

    assert chapters == []


@patch("core.utils.fetch_batch_with_retry")
@patch("core.utils.time.sleep")
@patch("core.utils.types.Part")
def test_images_to_md_success(mock_part, mock_sleep, mock_fetch_batch):
    """Test successful processing of images in batches and correct result mapping."""
    mock_part.from_bytes.return_value = "dummy_part"
    mock_fetch_batch.return_value = ["desc1", "desc2"]

    client = MagicMock()
    callback_mock = MagicMock()

    img_dict = {
        "img1.jpg": b"bytes1",
        "img2.jpg": b"bytes2",
    }

    batch_size = 2
    results = images_to_md(
        file_name="test_book.pdf",
        client=client,
        model="gemini-pro",
        prompt_text=f"Describe these {batch_size} images",
        api_delay=2,
        max_api_retries=3,
        img_dict=img_dict,
        batch_size=2,
        callback=callback_mock,
    )

    assert results == {
        "img1.jpg": "desc1",
        "img2.jpg": "desc2",
    }

    mock_fetch_batch.assert_called_once()
    callback_mock.assert_called_once_with(
        current=2,
        total=2,
        text="test_book.pdf images 2/2",
    )
    mock_sleep.assert_called_once_with(2)


@patch("core.utils.fetch_batch_with_retry")
@patch("core.utils.time.sleep")
@patch("core.utils.types.Part")
def test_images_to_md_skips_on_none_result(mock_part, mock_sleep, mock_fetch_batch):
    """Test that a batch is skipped safely if fetch_batch_with_retry returns None."""
    mock_part.from_bytes.return_value = "dummy_part"

    mock_fetch_batch.return_value = None

    client = MagicMock()
    callback_mock = MagicMock()

    img_dict = {
        "img1.jpg": b"bytes1",
    }

    results = images_to_md(
        file_name="test_book.pdf",
        client=client,
        model="gemini-pro",
        prompt_text="Describe",
        api_delay=1,
        max_api_retries=3,
        img_dict=img_dict,
        batch_size=1,
        callback=callback_mock,
    )

    assert results == {}
    mock_sleep.assert_not_called()


def test_get_file_hash(tmp_path):
    """Test computing sha256 hash for a file."""
    dummy_file = tmp_path / "test.txt"
    dummy_file.write_bytes(b"hello world")

    expected_hash = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"

    file_hash = get_file_hash(dummy_file)

    assert file_hash == expected_hash


def test_get_file_hash_custom_algorithm(tmp_path):
    """Test computing hash with a custom algorithm (e.g., md5)."""
    dummy_file = tmp_path / "test_md5.txt"
    dummy_file.write_bytes(b"hello world")

    expected_hash = "5eb63bbbe01eeed093cb22bb8f5acdc3"

    file_hash = get_file_hash(dummy_file, algorithm="md5")

    assert file_hash == expected_hash
