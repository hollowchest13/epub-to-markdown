from collections.abc import Callable
from pathlib import Path

from core.cleaner import clean_text
from core.models import BookFormat
from core.utils import (
    build_metadata,
    clean_filename,
    collect_chapters_from_text,
)
from storage.saver import save_all_chapters


def md_parser_pro(
    *, md_path: Path, output_dir: Path, callback: Callable[[int, int, str], None]
):
    file = md_path
    text = file.read_text(encoding="utf-8")
    text = clean_text(text=text)
    valid_chapters = collect_chapters_from_text(text=text, chapter_min_size=50)
    metadata = extract_md_metadata(md_path=file)
    save_all_chapters(
        valid_chapters=valid_chapters,
        output_dir=output_dir,
        metadata=metadata,
        callback=callback,
    )


def extract_md_metadata(md_path: Path) -> dict:
    content = md_path.read_text(encoding="utf-8")

    first_line_title = None
    for line in content.splitlines():
        if line.startswith("# "):
            first_line_title = line.lstrip("# ").strip()
            break

    return build_metadata(
        source_file=md_path,
        extra={
            "title": first_line_title or clean_filename(file_path=md_path),
            "author": [],
            "publisher": None,
            "published_date": None,
            "language": None,
            "description": None,
            "subjects": [],
            "file_type": BookFormat.MD.value,
        },
    )
