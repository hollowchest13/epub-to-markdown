import fitz
from pathlib import Path
from storage.saver import save_pdf_chapter, save_all_chapters
from utils import build_metadata, clean_filename, call_gemini_api
from google.genai import types
from google import genai
from models import BookFormat
import time
import re
import logging
from config import MAX_API_RETRIES, API_DELAY, CHAPTER_MIN_SIZE, PAGE_CHUNK_SIZE,MIN_CHUNK_LENGTH

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

def _get_chunk_text(*, client, model, max_retries, contents) -> str:
    chunk_text = ""
    for attempt in range(1, max_retries + 1):
        chunk_text = call_gemini_api(
            client=client,
            model=model,
            max_retries=max_retries,
            contents=contents,
            expect_json=False,
        )
        if len(chunk_text) < MIN_CHUNK_LENGTH:
            logger.warning(
                "Attempt %s/%s: result too short (%s characters).",
                attempt,
                max_retries,
                len(chunk_text),
            )
            time.sleep(API_DELAY)
            continue
        return chunk_text

    logger.error(
        "Failed to obtain a complete result after %s attempt(s).", max_retries
    )
    return chunk_text
    

def pdf_to_markdown_pro(*,
    pdf_path: Path, output_folder, client: genai.Client, model: str
):
    metadata = extract_pdf_metadata(pdf_path=pdf_path)
    chunks = split_pdf(pdf_path=pdf_path, chunk_size=PAGE_CHUNK_SIZE)
    full_text = ""
    prompt_text = (
        """Task: Extract the structural and textual content from the provided material and represent it in Markdown format for personal analysis and indexing.
            Guidelines:
            Process the provided text fragment in detail, maintaining the original structure, headings, and hierarchy.
            Use ONLY the provided source material. Ensure high fidelity to the original text; if a word is unclear, maintain its visual representation.
            TABLES: Format all data tables into standard Markdown tables.
            VISUALS: Provide a concise analytical description of any graphs, diagrams, or schemes, focusing on their main elements and logical connections (up to 100 words per item).
            LANGUAGE: Keep the output strictly in the original document's language.
            DATA CLEANING: Fix minor OCR artifacts (e.g., broken words, unnecessary line breaks) to improve readability.
            OUTPUT: Return the output as raw Markdown content. Focus on accuracy and technical formatting."""
    )

    # Process each chunk of the PDF separately and concatenate the resulting Markdown
    for i, chunk in enumerate(chunks):
        chunk_index = i + 1
        total_chunks = len(chunks)
        contents = [
            types.Part.from_bytes(data=chunk, mime_type="application/pdf"),
            prompt_text,
        ]
        chunk_text = _get_chunk_text(client=client,model=model,max_retries=MAX_API_RETRIES,contents=contents)
        full_text += (chunk_text or "").strip() + "\n\n"
        logger.info(f"in chunk {len(chunk_text.split())} words")
        logger.info(
            f"{metadata['title'][:30]} | Chunk: {chunk_index:03d}/{total_chunks:03d}"
        )
        # Small delay between chunks to avoid hammering the API
        time.sleep(API_DELAY)
    word_count = len(full_text.split())
    valid_chapters = collect_chapters_from_text(
        content=full_text, chapter_min_size=CHAPTER_MIN_SIZE
    )
    total_chapters = len(valid_chapters)
    save_all_chapters(
        valid_chapters=valid_chapters,
        output_folder=output_folder,
        metadata=metadata,
        saver=save_pdf_chapter,
    )
    logger.info(f"\nCompleted! {total_chapters} chapters → {output_folder}/")
    logger.info(f"Book: {metadata['title']} | ~{word_count:,} words")


def collect_chapters_from_text(
    *, content: str, chapter_min_size
) -> list[tuple[str, str]]:
    pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    chapters = []
    matches = list(pattern.finditer(content))
    if matches:
        intro_text = content[: matches[0].start()].strip()
        if len(intro_text) > chapter_min_size:
            chapters.append(("Introduction", intro_text))
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        chapter_name = match.group(2).strip()
        chapter_text = content[start:end].strip()
        if len(chapter_text) > chapter_min_size:
            chapters.append((chapter_name, chapter_text))
    if not chapters and len(content) > chapter_min_size:
        return [("Full Content", content)]
    return chapters

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
