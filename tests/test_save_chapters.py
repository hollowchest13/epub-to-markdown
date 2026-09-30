from unittest.mock import patch

from storage.saver import save_all_chapters, save_chapter


@patch("storage.saver.save_chapter")
def test_save_all_chapters(mock_save_chapter, tmp_path):
    output_dir = tmp_path / "test_book_output"
    chapters = [
        ("Chapter 1", "Content of chapter one"),
        ("Chapter 2", "Content of chapter two"),
    ]
    metadata = {"title": "Test Book", "author": "Unknown"}

    save_all_chapters(
        valid_chapters=chapters,
        output_dir=output_dir,
        metadata=metadata,
    )
    assert output_dir.is_dir()
    assert mock_save_chapter.call_count == 2

    mock_save_chapter.assert_any_call(
        content="Content of chapter one",
        chapter_name="Chapter 1",
        chapter_index=1,
        total_chapters=2,
        output_dir=output_dir,
        book_metadata=metadata,
        index=1,
    )


def test_save_chapter(tmp_path):
    # 1. Prepare input data
    content = "This is the text of our test chapter."
    chapter_name = "Chapter 1: The Beginning! (Part One)"
    book_metadata = {"title": "Test Book", "author": "Author"}

    # 2. Call the function (works live with the temporary directory)
    save_chapter(
        content=content,
        chapter_name=chapter_name,
        chapter_index=1,
        total_chapters=5,
        output_dir=tmp_path,
        book_metadata=book_metadata,
        index=1,
    )
    created_files = list(tmp_path.glob("001_*.md"))

    # Verify the file was created
    assert len(created_files) == 1, "Chapter file was not created!"

    # Verify the name was sanitized (no exclamation marks or brackets, lowercased)
    filename = created_files[0].name
    assert "chapter_1" in filename
    assert "!" not in filename
    assert "(" not in filename

    # Verify the content and frontmatter were written into the file
    file_text = created_files[0].read_text(encoding="utf-8")
    assert content in file_text
    assert "Test Book" in file_text
