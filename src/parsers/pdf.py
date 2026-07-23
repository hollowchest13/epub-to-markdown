import fitz
import pymupdf4llm
from pathlib import Path
from storage.saver import save_all_chapters
from utils import (
    build_metadata,
    clean_filename,
    call_gemini_api,
    collect_chapters_from_text,
)
from google.genai import types
from google import genai
from models import BookFormat
from cli.cleaner import clean_text
import time
import re
import logging
from config import (
    MAX_API_RETRIES,
    API_DELAY,
    CHAPTER_MIN_SIZE,
    MIN_CHUNK_LENGTH,
)

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

    # Process each chunk of the PDF separately and concatenate the resulting Markdown
    with fitz.open(str(pdf_path)) as doc:
        metadata = extract_pdf_metadata(doc, pdf_path=pdf_path)
        plan = build_processing_plan(doc)
        batches = _plan_to_bytes(doc, plan=plan)

    full_text = ""
    for i, (method, batch_bytes) in enumerate(batches, 1):
        chunk_text = _get_chunk_text(
            client=client,
            model=model,
            prompt_text=prompt_text,
            pdf_bytes=batch_bytes,
            max_retries=MAX_API_RETRIES,
            method=method,
        )
        full_text += (chunk_text or "").strip() + "\n\n"
        logger.info(f"in chunk {len(chunk_text.split())} words")
        logger.info(
            "%s | Batch: %03d/%03d | method: %s",
            metadata["title"][:30],
            i,
            len(batches),
            method,
        )
        # Small delay between chunks to avoid hammering the API
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
    doc, *, max_gemini_pages: int = 20
) -> list[tuple[str, list[int]]]:
    groups = []
    current_method = None
    current_pages = []

    for page in doc:
        method = "gemini" if assess_page(page) else "local"

        if method == current_method:
            current_pages.append(page.number)
            if method == "gemini" and len(current_pages) >= max_gemini_pages:
                groups.append((current_method, current_pages))
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
