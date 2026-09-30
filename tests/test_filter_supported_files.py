from core.utils import filter_supported_files


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
