import logging
import re
import time
from collections.abc import Callable
from pathlib import Path

import pymupdf as fitz
import pymupdf4llm
from google import genai
from google.genai import types

from config.config_manager import ConfigManager, PromptType
from core.cleaner import clean_text
from core.models import BookFormat
from core.utils import (
    build_metadata,
    clean_filename,
    collect_chapters_from_text,
    fetch_batch_with_retry,
)
from errors.api_errors import RateLimitExceeded
from parsers.base_parser import BaseParser
from storage.saver import save_all_chapters

logger = logging.getLogger(__name__)


class PdfParser(BaseParser):
    def __init__(self, *, config_manager: ConfigManager):
        super().__init__(config_manager=config_manager)
        self._model = config_manager.model
        self._api_delay = config_manager.api_delay
        self._max_api_retries = config_manager.max_api_retries
        self._chapter_min_size = config_manager.chapter_min_size
        self._img_chunk_size = config_manager.img_chunk_size
        self._min_chunk_lenght = config_manager.min_chunk_length
        self._prompt_text = self._prompt_dict[PromptType.PDF_PROMPT]

    def _extract_pdf_metadata(self, *, doc: fitz.Document, pdf_path: Path) -> dict:
        meta: dict = doc.metadata or {}

        return build_metadata(
            source_file=pdf_path,
            extra={
                "title": meta.get("title") or clean_filename(file_path=pdf_path),
                "author": [meta.get("author")],
                "publisher": meta.get("producer"),
                "published_date": meta.get("creationDate"),
                "language": meta.get("language"),
                "description": meta.get("subject"),
                "subjects": [meta.get("keywords")] if meta.get("keywords") else [],
                "file_type": BookFormat.PDF.value,
            },
        )

    def _get_chunk_text(
        self,
        *,
        pdf_bytes: bytes,
        method: str,
        client: genai.Client | None = None,
        on_rate_limit: Callable = lambda *args, **kwargs: None,
    ) -> str:
        if method == "gemini" and client is not None:
            try:
                contents = [
                    types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                    self._prompt_text,
                ]
                chunk_text = fetch_batch_with_retry(
                    client=client,
                    model=self._model,
                    api_delay=self._api_delay,
                    contents=contents,
                    max_api_retries=self._max_api_retries,
                    expect_json=False,
                )

                if chunk_text is not None:
                    text_str = str(chunk_text)
                    if len(text_str) >= self._min_chunk_lenght:
                        return text_str

                    logger.warning(
                        "Result too short (%s characters). Falling back to local",
                        len(text_str),
                    )
                else:
                    logger.warning("Result is None. Falling back to local conversion.")

            except RateLimitExceeded:
                on_rate_limit()
            except Exception as e:  # noqa: BLE001
                logger.error(
                    "Gemini API error: %s. Falling back to local conversion.", e
                )

        chunk_text = self._local_conversion(pdf_bytes=pdf_bytes)
        logger.info("Local result has %s characters.", len(chunk_text))
        return chunk_text

    def _local_conversion(self, *, pdf_bytes: bytes) -> str:
        text = ""
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            text = pymupdf4llm.to_markdown(doc)
        if not isinstance(text, str):
            raise TypeError(f"Expected str, got {type(text)}")
        return text

    def to_markdown(
        self,
        *,
        file_path: Path,
        output_dir,
        client: genai.Client | None = None,
        on_rate_limit: Callable = lambda *args, **kwargs: None,
        callback: Callable = lambda *args, **kwargs: None,
    ):

        with fitz.open(str(file_path)) as doc:
            metadata = self._extract_pdf_metadata(doc=doc, pdf_path=file_path)
            plan = self._build_processing_plan(doc=doc)
            for i, (method, pages) in enumerate(plan, 1):
                logger.info(
                    "Plan %03d/%03d | method: %s | pages: %s",
                    i,
                    len(plan),
                    method,
                    pages,
                )
            batches = self._plan_to_bytes(doc=doc, plan=plan)

        full_text = ""
        total_pages = sum(len(page_nums) for _, page_nums in plan)
        processed_pages = 0
        for i, ((method, page_nums), (_, batch_bytes)) in enumerate(
            zip(plan, batches), 1
        ):
            chunk_text = self._get_chunk_text(
                client=client,
                pdf_bytes=batch_bytes,
                method=method,
                on_rate_limit=on_rate_limit,
            )
            safe_chunk = chunk_text or ""
            full_text += safe_chunk.strip() + "\n\n"
            processed_pages += len(page_nums)
            callback(
                current=processed_pages,
                total=total_pages,
                text=f"{file_path.stem} page {processed_pages}/{total_pages}",
            )

            logger.info(
                "%s | Batch: %03d/%03d | method: %s | pages: %d | words: %d \n",
                metadata["title"][:30],
                i,
                len(batches),
                method,
                len(page_nums),
                len(safe_chunk.split()),
            )
            time.sleep(self._api_delay)

        full_text = clean_text(full_text)
        word_count = len(full_text.split())
        valid_chapters = collect_chapters_from_text(
            text=full_text, chapter_min_size=self._chapter_min_size
        )
        total_chapters = len(valid_chapters)
        save_all_chapters(
            valid_chapters=valid_chapters,
            output_dir=output_dir,
            metadata=metadata,
            callback=callback,
        )
        logger.info(f"\nCompleted! {total_chapters} chapters → {output_dir}/")
        logger.info(f"Book: {metadata['title']} | ~{word_count:,} words")

    MATH_PATTERN = re.compile(r"[∑∫∏√±×÷≠≤≥∞αβγδεζηθλμπσφψω]")

    def _assess_page(
        self,
        page,
        *,
        min_text_length: int = 50,
        math_symbol_threshold: int = 5,
        image_size_ratio: float = 0.05,
    ) -> bool:
        is_scanned = len(page.get_text().strip()) < min_text_length
        has_math = (
            len(self.MATH_PATTERN.findall(page.get_text())) > math_symbol_threshold
        )
        has_images = self._has_significant_images(page, size_ratio=image_size_ratio)
        return is_scanned or has_math or has_images

    def _build_processing_plan(
        self, doc, *, max_pages_per_batch: int = 20
    ) -> list[tuple[str, list[int]]]:
        groups = []
        current_method = None
        current_pages = []

        for page in doc:
            method = "gemini" if self._assess_page(page) else "local"

            if method == current_method:
                current_pages.append(page.number)
                if len(current_pages) >= max_pages_per_batch:
                    groups.append((current_method, current_pages))
                    current_method = None
                    current_pages = []
            else:
                if current_pages:
                    groups.append((current_method, current_pages))
                current_method = method
                current_pages = [page.number]

        if current_pages:
            groups.append((current_method, current_pages))

        return groups

    def _plan_to_bytes(
        self, doc, *, plan: list[tuple[str, list[int]]]
    ) -> list[tuple[str, bytes]]:
        """Converts the plan into a batch of bytes."""
        result = []
        for method, pages in plan:
            with fitz.open() as writer:
                for page_num in pages:
                    writer.insert_pdf(doc, from_page=page_num, to_page=page_num)
                result.append((method, writer.tobytes()))
        return result

    def _has_significant_images(
        self, page: fitz.Page, *, size_ratio: float = 0.05
    ) -> bool:
        page_area = page.rect.width * page.rect.height
        for img in page.get_image_info():
            bbox = img.get("bbox")
            if bbox:
                img_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                if img_area / page_area > size_ratio:
                    return True
        return False
