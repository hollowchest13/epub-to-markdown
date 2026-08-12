import logging
import re
import time
from collections.abc import Callable
from pathlib import Path

import pymupdf as fitz
import pymupdf4llm
from google import genai
from google.genai import types

from config.config import (
    API_DELAY,
    CHAPTER_MIN_SIZE,
    MAX_API_RETRIES,
    MIN_CHUNK_LENGTH,
)
from core.cleaner import clean_text
from core.models import BookFormat
from core.utils import (
    build_metadata,
    call_gemini_api,
    clean_filename,
    collect_chapters_from_text,
)
from storage.saver import save_all_chapters

logger = logging.getLogger(__name__)


def extract_pdf_metadata(doc: fitz.Document, pdf_path: Path) -> dict:
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
    *,
    client: genai.Client,
    model: str,
    prompt_text: str,
    pdf_bytes: bytes,
    max_retries: int,
    method: str,
) -> str:
    if method == "gemini":
        try:
            contents = [
                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                prompt_text,
            ]
            chunk_text = call_gemini_api(
                client=client,
                model=model,
                max_retries=max_retries,
                contents=contents,
                expect_json=False,
            )
            if len(chunk_text) >= MIN_CHUNK_LENGTH:
                return chunk_text
            logger.warning(
                "Result too short (%s characters). Falling back to local",
                len(chunk_text),
            )
        except Exception:
            logger.exception("Gemini API error: %s. Falling back to local conversion.")

    chunk_text = _local_conversion(pdf_bytes=pdf_bytes)
    logger.info("Local result has %s characters.", len(chunk_text))
    return chunk_text


def _local_conversion(*, pdf_bytes: bytes) -> str:
    text = ""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        text = pymupdf4llm.to_markdown(doc)
    if not isinstance(text, str):
        raise TypeError(f"Expected str, got {type(text)}")
    return text


def pdf_to_markdown_pro(
    *,
    pdf_path: Path,
    output_dir,
    client: genai.Client,
    model: str,
    callback: Callable = lambda *args, **kwargs: None,
):
    prompt_text = """Task: Extract the structural and textual content from the provided material and represent it in Markdown format for personal analysis and indexing.
            Guidelines:
            Process the provided text fragment in detail, maintaining the original structure, headings, and hierarchy.
            Use ONLY the provided source material. Ensure high fidelity to the original text; if a word is unclear, maintain its visual representation.
            TABLES: Format all data tables into standard Markdown tables.
            VISUALS: Provide a concise analytical description of any graphs, diagrams, or schemes, focusing on their main elements and logical connections (up to 100 words per item).
            LANGUAGE: Keep the output strictly in the original document's language.
            DATA CLEANING: Fix minor OCR artifacts (e.g., broken words, unnecessary line breaks) to improve readability.
            OUTPUT: Return the output as raw Markdown content. Focus on accuracy and technical formatting."""

    with fitz.open(str(pdf_path)) as doc:
        metadata = extract_pdf_metadata(doc, pdf_path=pdf_path)
        plan = build_processing_plan(doc)
        for i, (method, pages) in enumerate(plan, 1):
            logger.info(
                "Plan %03d/%03d | method: %s | pages: %s", i, len(plan), method, pages
            )
        batches = _plan_to_bytes(doc, plan=plan)

    full_text = ""
    total_pages = sum(len(page_nums) for _, page_nums in plan)
    processed_pages = 0
    for i, ((method, page_nums), (_, batch_bytes)) in enumerate(zip(plan, batches), 1):
        chunk_text = _get_chunk_text(
            client=client,
            model=model,
            prompt_text=prompt_text,
            pdf_bytes=batch_bytes,
            max_retries=MAX_API_RETRIES,
            method=method,
        )
        full_text += (chunk_text or "").strip() + "\n\n"
        processed_pages += len(page_nums)
        callback(
            current=processed_pages,
            total=total_pages,
            text=f"{pdf_path.stem} page {processed_pages}/{total_pages}",
        )
        logger.info(
            "%s | Batch: %03d/%03d | method: %s | pages: %d | words: %d \n",
            metadata["title"][:30],
            i,
            len(batches),
            method,
            len(page_nums),
            len(chunk_text.split()),
        )
        time.sleep(API_DELAY)

    full_text = clean_text(full_text)
    word_count = len(full_text.split())
    valid_chapters = collect_chapters_from_text(
        text=full_text, chapter_min_size=CHAPTER_MIN_SIZE
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


def assess_page(
    page,
    *,
    min_text_length: int = 50,
    math_symbol_threshold: int = 5,
    image_size_ratio: float = 0.05,
) -> bool:
    is_scanned = len(page.get_text().strip()) < min_text_length
    has_math = len(MATH_PATTERN.findall(page.get_text())) > math_symbol_threshold
    has_images = _has_significant_images(page, size_ratio=image_size_ratio)
    return is_scanned or has_math or has_images


def build_processing_plan(
    doc, *, max_pages_per_batch: int = 20
) -> list[tuple[str, list[int]]]:
    groups = []
    current_method = None
    current_pages = []

    for page in doc:
        method = "gemini" if assess_page(page) else "local"

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
    doc, *, plan: list[tuple[str, list[int]]]
) -> list[tuple[str, bytes]]:
    """Converts the plan into a batch of bytes."""
    result = []
    for method, pages in plan:
        with fitz.open() as writer:
            for page_num in pages:
                writer.insert_pdf(doc, from_page=page_num, to_page=page_num)
            result.append((method, writer.tobytes()))
    return result


def _has_significant_images(page: fitz.Page, *, size_ratio: float = 0.05) -> bool:
    page_area = page.rect.width * page.rect.height
    for img in page.get_image_info():
        bbox = img.get("bbox")
        if bbox:
            img_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            if img_area / page_area > size_ratio:
                return True
    return False
