from unittest.mock import MagicMock, patch

import pytest

from parsers.md import MdParser


@pytest.fixture
def mock_parser(mock_config_manager: MagicMock) -> MdParser:
    return MdParser(config_manager=mock_config_manager)


def test_extract_md_metadata_with_heading(mock_parser, tmp_path):
    """Scenario: markdown file contains a heading starting with '# ' -> extracts it as title."""
    md_file = tmp_path / "test_doc.md"
    md_file.write_text("# My Custom Title\nSome content here...", encoding="utf-8")

    with (
        patch("parsers.md.build_metadata") as mock_build,
        patch("parsers.md.clean_filename") as mock_clean,
    ):
        mock_build.return_value = {"status": "md_success"}

        result = mock_parser._extract_md_metadata(md_path=md_file)

        mock_build.assert_called_once()
        _, kwargs = mock_build.call_args

        assert kwargs["source_file"] == md_file
        extra = kwargs["extra"]
        assert extra["title"] == "My Custom Title"
        assert extra["author"] == []
        assert extra["publisher"] is None
        assert extra["published_date"] is None
        assert extra["language"] is None
        assert extra["description"] is None
        assert extra["subjects"] == []

        mock_clean.assert_not_called()
        assert result == {"status": "md_success"}


def test_extract_md_metadata_fallback_filename(mock_parser, tmp_path):
    """Scenario: markdown file has no heading -> falls back to clean_filename for title."""
    md_file = tmp_path / "document_without_heading.md"
    md_file.write_text(
        "Just plain text without headers.\nAnother line.", encoding="utf-8"
    )

    with (
        patch("parsers.md.build_metadata") as mock_build,
        patch(
            "parsers.md.clean_filename", return_value="Clean Markdown Name"
        ) as mock_clean,
    ):
        mock_parser._extract_md_metadata(md_path=md_file)

        mock_clean.assert_called_once_with(file_path=md_file)

        _, kwargs = mock_build.call_args
        extra = kwargs["extra"]
        assert extra["title"] == "Clean Markdown Name"
        assert extra["author"] == []
        assert extra["publisher"] is None
