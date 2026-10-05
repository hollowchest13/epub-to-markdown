from unittest.mock import MagicMock, patch

from core.converter import convert_to_md


@patch("core.converter.EpubParser")
@patch("core.converter.PdfParser")
@patch("core.converter.MdParser")
def test_convert_to_md_success(
    mock_md_parser_cls, mock_pdf_parser_cls, mock_epub_parser_cls, tmp_path
):
    """Verify correct parser selection and invocation for epub, pdf, and md files."""
    mock_client = MagicMock()
    mock_config = MagicMock()
    target_dir = tmp_path / "output"

    epub_instance = mock_epub_parser_cls.return_value
    pdf_instance = mock_pdf_parser_cls.return_value
    md_instance = mock_md_parser_cls.return_value

    files = [
        tmp_path / "book.epub",
        tmp_path / "doc.pdf",
        tmp_path / "notes.md",
    ]

    convert_to_md(
        files,
        client=mock_client,
        config_manager=mock_config,
        target_dir=target_dir,
    )

    mock_epub_parser_cls.assert_called_once_with(config_manager=mock_config)
    mock_pdf_parser_cls.assert_called_once_with(config_manager=mock_config)
    mock_md_parser_cls.assert_called_once_with(config_manager=mock_config)

    epub_instance.to_markdown.assert_called_once()
    call_kwargs = epub_instance.to_markdown.call_args.kwargs
    assert call_kwargs["file_path"] == files[0]
    assert call_kwargs["output_dir"] == target_dir / "book"
    assert call_kwargs["client"] == mock_client

    assert epub_instance.to_markdown.call_count == 1
    assert pdf_instance.to_markdown.call_count == 1
    assert md_instance.to_markdown.call_count == 1


@patch("core.converter.EpubParser")
def test_convert_to_md_handles_errors_and_unsupported(mock_epub_parser_cls, tmp_path):
    """Verify that unsupported files are skipped and exceptions in one file don't break the batch."""
    mock_client = MagicMock()
    mock_config = MagicMock()
    target_dir = tmp_path / "output"

    epub_instance = mock_epub_parser_cls.return_value

    epub_instance.to_markdown.side_effect = [Exception("Parsing error"), None]

    files = [
        tmp_path / "broken.epub",
        tmp_path / "unsupported.txt",
        tmp_path / "good.epub",
    ]

    convert_to_md(
        files,
        client=mock_client,
        config_manager=mock_config,
        target_dir=target_dir,
    )

    assert epub_instance.to_markdown.call_count == 3
