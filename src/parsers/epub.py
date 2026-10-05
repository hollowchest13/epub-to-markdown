import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub
from google import genai
from markdownify import markdownify as md

from config.config_manager import ConfigManager, PromptType
from core.cleaner import clean_text
from core.models import BookFormat
from core.utils import build_metadata, clean_filename, images_to_md
from errors.api_errors import RateLimitExceeded
from parsers.base_parser import BaseParser
from storage.saver import save_all_chapters

logger = logging.getLogger(__name__)


class EpubParser(BaseParser):
    def __init__(self, config_manager: ConfigManager):
        super().__init__(config_manager=config_manager)
        self._config_manager = config_manager
        self._model = config_manager.model
        self._api_delay = config_manager.api_delay
        self._max_api_retries = config_manager.max_api_retries
        self._chapter_min_size = config_manager.chapter_min_size
        self._img_chunk_size = config_manager.img_chunk_size
        self._prompt_text = self._prompt_dict[PromptType.IMAGE_PROMPT]

    def _extract_epub_metadata(self, book: epub.EpubBook, *, epub_path: Path):
        def first(key: str):
            values: Any = book.get_metadata("DC", key)
            # Checking: does the list exist, does it have a first element, and does the element have a value?
            if values and isinstance(values[0], (list, tuple)) and len(values[0]) > 0:
                return values[0][0]

            # If it is just a string (sometimes metadata returns (value,))
            if values and isinstance(values[0], str):
                return values[0]
            return None

        def all_values(key):
            metadata = book.get_metadata("DC", key)
            results = []
            for v in metadata:
                if isinstance(v, (list, tuple)) and len(v) > 0:
                    results.append(v[0])
                elif isinstance(v, str):
                    results.append(v)
            return results

        raw_description = first("description")
        cleaned_description = clean_text(raw_description) if raw_description else None

        # Page count (number of spine documents as an approximate estimate)
        spine_ids = [item_id for item_id, _ in book.spine]
        total_spine_items = len(spine_ids)

        # Word count for the entire text
        total_words = 0
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), "html.parser")
            total_words += len(soup.get_text().split())

        return build_metadata(
            source_file=epub_path,
            extra={
                "title": first("title") or clean_filename(file_path=epub_path),
                "author": all_values("creator"),
                "publisher": first("publisher"),
                "published_date": first("date"),
                "language": first("language"),
                "identifier": first("identifier"),
                "rights": first("rights"),
                "description": cleaned_description,
                "subjects": all_values("subject"),
                "total_spine_items": total_spine_items,
                "estimated_total_words": total_words,
                "file_type": BookFormat.EPUB.value,
            },
        )

    def _extract_chapter_text(
        self, *, item, image_descriptions: dict[str, str], strip_nav: bool = True
    ) -> tuple[str, BeautifulSoup]:
        """Shared logic for cleaning item content:
        decoding, removing junk tags, replacing images, and converting to Markdown."""

        content = item.get_content()
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")

        soup = BeautifulSoup(content, "html.parser")

        if strip_nav:
            for tag in soup.find_all(["script", "style", "nav"]):
                tag.decompose()

        soup = self._replace_images(soup=soup, image_descriptions=image_descriptions)
        text = md(str(soup))
        text = clean_text(text)
        return text, soup

    def _collect_epub_chapters(
        self,
        *,
        book: epub.EpubBook,
        client: genai.Client | None = None,
        on_rate_limit: Callable = lambda *args, **kwargs,: None,
        callback: Callable = lambda *args, **kwargs: None,
    ) -> list[tuple[str, str]]:
        spine_ids = [item_id for item_id, _ in book.spine]
        ordered_items = [book.get_item_with_id(item_id) for item_id in spine_ids]
        img_dict = self._get_epub_images(book=book)
        image_descriptions = {}
        if client:
            try:
                image_descriptions = (
                    images_to_md(
                        file_name=book.title,
                        client=client,
                        model=self._model,
                        img_dict=img_dict,
                        prompt_text=self._prompt_text,
                        batch_size=self._img_chunk_size,
                        max_api_retries=self._max_api_retries,
                        api_delay=self._api_delay,
                        callback=callback,
                    )
                    if img_dict
                    else {}
                )
            except RateLimitExceeded:
                on_rate_limit()

            except Exception:
                logger.exception(
                    "Failed to generate image descriptions; continuing without them"
                )

        valid_chapters = []

        # Main cycle
        for item in ordered_items:
            if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
                continue
            try:
                text, soup = self._extract_chapter_text(
                    item=item, image_descriptions=image_descriptions, strip_nav=True
                )

                if len(text) > self._chapter_min_size:
                    header = soup.find(["h1", "h2", "h3"])
                    header_text = header.get_text().strip() if header else ""
                    chapter_name = (
                        header_text
                        if header_text
                        else f"Chapter {len(valid_chapters) + 1}"
                    )
                    valid_chapters.append((chapter_name, text))
            except Exception:
                logger.exception("Error processing item during main loop")

        # Fallback
        if not valid_chapters:
            all_text = []
            for item in ordered_items:
                if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
                    continue
                try:
                    text, _ = self._extract_chapter_text(
                        item=item, image_descriptions=image_descriptions, strip_nav=True
                    )
                    if text.strip():
                        all_text.append(text)
                except Exception:
                    logger.exception(
                        "Error processing item during fallback loop",
                    )

            return [("Full content", "\n\n".join(all_text))]

        return valid_chapters

    def _get_epub_images(self, *, book: epub.EpubBook) -> dict[str, bytes]:
        images: dict = {}
        for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
            img_bytes = item.get_content()
            img_name = item.get_name()
            images[img_name] = img_bytes
        return images

    def _replace_images(self, *, soup, image_descriptions: dict[str, str]):
        # Normalize description keys — filename only.
        by_filename = {Path(k).name: v for k, v in image_descriptions.items()}

        for img_tag in soup.find_all("img"):
            src = img_tag.get("src")
            if not src:
                continue
            filename = Path(src).name
            if filename in by_filename:
                new_tag = soup.new_tag("p")
                new_tag.string = by_filename[filename]
                img_tag.replace_with(new_tag)
        return soup

    def to_markdown(
        self,
        *,
        file_path: Path,
        output_dir: Path,
        client: genai.Client | None = None,
        on_rate_limit: Callable = lambda *args, **kwargs: None,
        callback: Callable = lambda *args, **kwargs: None,
    ):
        book = epub.read_epub(file_path)
        metadata = self._extract_epub_metadata(book=book, epub_path=file_path)
        valid_chapters = self._collect_epub_chapters(
            book=book,
            client=client,
            on_rate_limit=on_rate_limit,
            callback=callback,
        )
        total_chapters = len(valid_chapters)
        save_all_chapters(
            valid_chapters=valid_chapters,
            output_dir=output_dir,
            metadata=metadata,
            callback=callback,
        )

        logger.info("Completed! %s chapters → %s/", total_chapters, output_dir)
        logger.info(
            "Book: %s | ~%s words", metadata["title"], metadata["estimated_total_words"]
        )
