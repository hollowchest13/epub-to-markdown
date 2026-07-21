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
import logging
from config import (
    MAX_API_RETRIES,
    API_DELAY,
    CHAPTER_MIN_SIZE,
    PAGE_CHUNK_SIZE,
    MIN_CHUNK_LENGTH,
)

logger = logging.getLogger(__name__)


def extract_pdf_metadata(pdf_path: Path) -> dict:
    with fitz.open(str(pdf_path)) as doc:
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
    only_local: bool,
) -> str:

    if not only_local:
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
            "Result too short (%s characters).Try tonverting with pymupdf4llm",
            len(chunk_text),
        )
    chunk_text = _local_conversion(pdf_bytes=pdf_bytes)
    logger.info(
        "Local result has %s characters.",
        len(chunk_text),
    )
    return chunk_text


def _local_conversion(*, pdf_bytes: bytes) -> str:
    text = ""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        text = pymupdf4llm.to_markdown(doc)
    assert isinstance(text, str), f"Expected str, got {type(text)}"
    return text


def pdf_to_markdown_pro(
    *,
    pdf_path: Path,
    output_dir,
    client: genai.Client,
    model: str,
    only_local: bool = False,
):
    metadata = extract_pdf_metadata(pdf_path=pdf_path)
    chunks = split_pdf(pdf_path=pdf_path, chunk_size=PAGE_CHUNK_SIZE)
    full_text = ""
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
    for i, chunk in enumerate(chunks):
        chunk_index = i + 1
        total_chunks = len(chunks)
        chunk_text = _get_chunk_text(
            client=client,
            model=model,
            prompt_text=prompt_text,
            pdf_bytes=chunk,
            max_retries=MAX_API_RETRIES,
            only_local=only_local,
        )
        full_text += (chunk_text or "").strip() + "\n\n"
        logger.info(f"in chunk {len(chunk_text.split())} words")
        logger.info(
            f"{metadata['title'][:30]} | Chunk: {chunk_index:03d}/{total_chunks:03d}"
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


def split_pdf(*, pdf_path: Path, chunk_size: int) -> list[bytes]:
    with fitz.open(str(pdf_path)) as doc:
        chunks: list[bytes] = []
        for i in range(0, len(doc), chunk_size):
            with fitz.open() as writer:
                writer.insert_pdf(
                    doc, from_page=i, to_page=min(i + chunk_size - 1, len(doc) - 1)
                )
                chunks.append(writer.tobytes())
        return chunks
