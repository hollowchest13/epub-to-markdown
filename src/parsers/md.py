from collections.abc import Callable
from pathlib import Path

from google import genai

from config.config_manager import ConfigManager
from core.cleaner import clean_text
from core.models import BookFormat
from core.utils import (
    build_metadata,
    clean_filename,
    collect_chapters_from_text,
)
from parsers.base_parser import BaseParser
from storage.saver import save_all_chapters


class MdParser(BaseParser):
    def __init__(self, *, config_manager: ConfigManager):
        super().__init__(config_manager=config_manager)
        self._chapter_min_size = config_manager.chapter_min_size

    def to_markdown(
        self,
        *,
        file_path: Path,
        output_dir: Path,
        client: genai.Client | None = None,
        on_rate_limit: Callable = lambda *args, **kwargs: None,
        callback: Callable = lambda *args, **kwargs: None,
    ):
        text = file_path.read_text(encoding="utf-8")
        text = clean_text(text=text)
        valid_chapters = collect_chapters_from_text(text=text, chapter_min_size=50)
        metadata = self._extract_md_metadata(md_path=file_path)
        save_all_chapters(
            valid_chapters=valid_chapters,
            output_dir=output_dir,
            metadata=metadata,
            callback=callback,
        )

    def _extract_md_metadata(self, *, md_path: Path) -> dict:
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
