from pathlib import Path
import yaml
import re
import logging
import shutil


logger = logging.getLogger(__name__)


def _build_frontmatter(
    content: str,
    chapter_name: str,
    chapter_index: int,
    total_chapters: int,
    book_metadata: dict,
    extra: dict | None = None,
) -> dict:
    frontmatter = {
        # --- Книга ---
        "title": book_metadata.get("title", "Unknown"),
        "author": book_metadata.get("author", ["Unknown"]),
        "publisher": book_metadata.get("publisher"),
        "published_date": book_metadata.get("published_date"),
        "language": book_metadata.get("language"),
        "identifier": book_metadata.get("identifier"),
        "rights": book_metadata.get("rights"),
        "description": book_metadata.get("description"),
        "subjects": book_metadata.get("subjects", []),
        # --- Розділ ---
        "chapter": chapter_name,
        "chapter_index": chapter_index,
        "total_chapters": total_chapters,
        "word_count": len(content.split()),
        # --- Файл ---
        "source_file": book_metadata.get("source_file"),
        "file_type": book_metadata.get("file_type"),
        "file_size_kb": book_metadata.get("file_size_kb"),
        "file_hash_sha256": book_metadata.get("file_hash_sha256"),
        # --- Конвертація ---
        "converted_date": book_metadata.get("converted_date"),
        "converted_at": book_metadata.get("converted_at"),
        **(extra or {}),
    }
    return {k: v for k, v in frontmatter.items() if v is not None and v != []}


def _write_chapter_file(
    content: str,
    frontmatter: dict,
    file_path: Path,
) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.dump(frontmatter, f, allow_unicode=True, default_flow_style=False)
        f.write("---\n\n")
        f.write(content)


def save_chapter(
    content: str,
    chapter_name: str,
    chapter_index: int,
    total_chapters: int,
    output_dir: Path,
    book_metadata: dict,
    index: int,
) -> None:
    safe_name = re.sub(r"[^\w\-]", "_", chapter_name).lower()[:50]
    file_path = Path(output_dir) / f"{index:03d}_{safe_name}.md"
    frontmatter = _build_frontmatter(
        content, chapter_name, chapter_index, total_chapters, book_metadata
    )
    _write_chapter_file(content, frontmatter, file_path)


def save_all_chapters(
    *,
    valid_chapters: list[tuple[str, str]],
    output_dir: Path,
    metadata: dict,
) -> None:
    total_chapters = len(valid_chapters)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for index, (chapter_name, text) in enumerate(valid_chapters, start=1):
        save_chapter(
            content=text,
            chapter_name=chapter_name,
            chapter_index=index,
            total_chapters=total_chapters,
            output_dir=output_dir,
            book_metadata=metadata,
            index=index,
        )
        logger.info(f"[{index}/{total_chapters}] Saved: {chapter_name}")
