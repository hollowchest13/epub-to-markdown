import fitz
from pathlib import Path
from src.saver import save_pdf_chapter,save_all_chapters
from src.utils import build_metadata, clean_filename,call_gemini_api
from google.genai import types
from src.models import BookFormat
from google import genai
import time
import re
import logging
from src.config import MAX_API_RETRIES,API_DELAY,CHAPTER_MIN_SIZE,PAGE_CHUNK_SIZE
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_pdf_metadata(pdf_path: Path) -> dict:
    doc = fitz.open(str(pdf_path))
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
        },
    )
def pdf_to_markdown_pro(pdf_path: Path, output_folder, client: genai.Client, model: str):
    if not Path(output_folder).exists():
        Path(output_folder).mkdir(parents=True, exist_ok=True)

    file_type = BookFormat.PDF
    metadata = extract_pdf_metadata(pdf_path=pdf_path)
    chunks = split_pdf(pdf_path=pdf_path, chunk_size=PAGE_CHUNK_SIZE)
    full_text = ""
    prompt_text = (
       "Task: Convert the provided PDF chunk into Markdown format. "
        "Strict Rules:\n"
        "1. COMPLETELY convert the document without omissions, abbreviations, summarizing, or shortening. Process every page, paragraph, and heading.\n"
        "2. Use ONLY the provided text. If unsure about specific words, leave them as they visually appear.\n"
        "3. Preserve the document structure: text headings, lists, and tables.\n"
        "4. TABLES: Convert tables strictly into Markdown table format.\n"
        "5. VISUALS: If you encounter a graph, diagram, scheme, flowchart, or mind map, provide a text description (up to 100 words) directly in the text flow, specifying its type, main elements, connections, and key conclusion.\n"
        "6. LANGUAGE: Return all converted text, tables, and visual descriptions in the original document's language, NOT in English.\n"
        "7. OCR: Correct obvious text layer or OCR errors (broken words, accidental spaces).\n"
        "8. OUTPUT: Return ONLY the raw Markdown content."
    )

    # Process each chunk of the PDF separately and concatenate the resulting Markdown
    for i,chunk in enumerate(chunks):
        chunk_index = i + 1
        total_chunks = len(chunks)
        contents = [
            types.Part.from_bytes(data=chunk, mime_type="application/pdf"),
            prompt_text,
        ]
        chunk_text = call_gemini_api(
            client=client,
            model=model,
            max_retries=MAX_API_RETRIES,
            contents=contents,
            expect_json=False,
        )
        full_text += chunk_text or ""
        logger.info(f"{metadata['title'][:30]} | Чанк: {chunk_index:03d}/{total_chunks:03d}")
        # Small delay between chunks to avoid hammering the API
        time.sleep(API_DELAY)

    word_count = len(full_text.split())
    valid_chapters = collect_chapters_from_text(content=full_text,chapter_min_size=CHAPTER_MIN_SIZE)
    total_chapters = len(valid_chapters)
    save_all_chapters(
        valid_chapters=valid_chapters,
        output_folder=output_folder,
        metadata=metadata,
        file_type=file_type,
        saver=save_pdf_chapter
    )
    logger.info(f"\nГотово! {total_chapters} розділів → {output_folder}/")
    logger.info(f"Книга: {metadata['title']} | ~{word_count:,} слів")


def collect_chapters_from_text(*, content: str,chapter_min_size) -> list[tuple[str, str]]:
    pattern=re.compile(r"^(#{1,3})\s+(.+)$",re.MULTILINE)
    chapters = []
    matches=list(pattern.finditer(content))
    if matches:
        intro_text=content[:matches[0].start()].strip()
        if len(intro_text)>chapter_min_size:
            chapters.append(("Inroduction",intro_text))
    for i,match in enumerate(matches):
        start=match.end()
        end=matches[i+1].start() if i+1<len(matches) else len(content)
        chapter_name=match.group(2).strip()
        chapter_text=content[start:end].strip()
        if len(chapter_text)>chapter_min_size:
            chapters.append((chapter_name,chapter_text))
    if not chapters and len(content) > chapter_min_size:
        return [("Full Content", content)]
    return chapters

def split_pdf(*, pdf_path: Path, chunk_size: int) -> list[bytes]:
    doc = fitz.open(str(pdf_path))
    chunks: list[bytes] = []
    for i in range(0, len(doc), chunk_size):
        writer = fitz.open()
        writer.insert_pdf(
            doc, from_page=i, to_page=min(i + chunk_size - 1, len(doc) - 1)
        )
        chunks.append(writer.tobytes())
    return chunks
