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
    chunks = split_pdf(pdf_path=pdf_path, chunk_size=80)
    full_text = ""
    max_retries = 5

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
    for chunk in chunks:
        contents = [
            types.Part.from_bytes(data=chunk, mime_type="application/pdf"),
            prompt_text,
        ]
        chunk_text = call_gemini_api(
            client=client,
            model=model,
            max_retries=max_retries,
            contents=contents,
            expect_json=False,
        )
        full_text += chunk_text or ""
        # Small delay between chunks to avoid hammering the API
        time.sleep(6)

    word_count = len(full_text.split())
    valid_chapters = collect_chapters_from_text(content=full_text)
    total_chapters = len(valid_chapters)
    metadata = extract_pdf_metadata(pdf_path=pdf_path)
    save_all_chapters(
        valid_chapters=valid_chapters,
        output_folder=output_folder,
        metadata=metadata,
        file_type=file_type,
        saver=save_pdf_chapter
    )
    logger.info(f"\nГотово! {total_chapters} розділів → {output_folder}/")
    logger.info(f"Книга: {metadata['title']} | ~{word_count:,} слів")


def collect_chapters_from_text(*, content: str) -> list[tuple[str, str]]:
    parts = re.split(r"^(#{1,3} .+)$", content, flags=re.MULTILINE)

    valid_chapters = []
    if parts[0].strip() and len(parts[0].strip()) > 100:
        valid_chapters.append(("Introduction", parts[0].strip()))
    i = 1
    while i < len(parts) - 1:
        chapter_name = parts[i].lstrip("# ").strip()
        text = parts[i + 1].strip()
        if len(text) > 200:
            valid_chapters.append((chapter_name, text))
        i += 2

    return valid_chapters

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
