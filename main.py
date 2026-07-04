import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import re
import json
import time
from enum import Enum
from pathlib import Path
from google import genai
from utils import clean_markdown
from google.genai import types
from google.genai.errors import ClientError
from epub import extract_epub_metadata, get_epub_images, replace_images
from pdf import extract_pdf_metadata, split_pdf
from saver import save_epub_chapter, save_pdf_chapter
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
client = genai.Client()


class BookFormat(Enum):
    EPUB = ".epub"
    PDF = ".pdf"


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


def collect_epub_chapters(*, book) -> list[tuple[str, str]]:
    spine_ids = [item_id for item_id, _ in book.spine]
    ordered_items = [book.get_item_with_id(item_id) for item_id in spine_ids]
    img_dict = get_epub_images(book=book)
    image_descriptions = images_to_md(img_dict=img_dict) if img_dict else {}

    # Перший прохід — збираємо валідні розділи, щоб знати total_chapters
    valid_chapters = []
    for item in ordered_items:
        if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        soup = BeautifulSoup(item.get_content(), "html.parser")
        for tag in soup.find_all(["script", "style", "nav"]):
            tag.decompose()
        soup = replace_images(soup, image_descriptions)
        text = md(str(soup))
        text = clean_markdown(text)
        if len(text) > 200:
            header = soup.find(["h1", "h2", "h3"])
            chapter_name = (
                header.get_text().strip()
                if header
                else f"Chapter {len(valid_chapters) + 1}"
            )
            valid_chapters.append((chapter_name, text))
    return valid_chapters


CHAPTER_SAVERS: dict = {
    BookFormat.EPUB: save_epub_chapter,
    BookFormat.PDF: save_pdf_chapter,
}


def save_all_chapters(
    *,
    valid_chapters: list[tuple[str, str]],
    output_folder: str,
    metadata: dict,
    file_type: BookFormat,
) -> None:
    total_chapters = len(valid_chapters)
    for index, (chapter_name, text) in enumerate(valid_chapters, start=1):
        CHAPTER_SAVERS[file_type](
            content=text,
            chapter_name=chapter_name,
            chapter_index=index,
            total_chapters=total_chapters,
            output_folder=output_folder,
            book_metadata=metadata,
            index=index,
        )
        logger.info(f"[{index}/{total_chapters}] Збережено: {chapter_name}")


def epub_to_markdown_pro(epub_path, output_folder):
    if not Path.exists(output_folder):
        Path.mkdir(output_folder, parents=True, exist_ok=True)
    file_type = BookFormat.EPUB

    book = epub.read_epub(epub_path)
    metadata = extract_epub_metadata(book=book, epub_path=epub_path)
    valid_chapters = collect_epub_chapters(book=book)
    total_chapters = len(valid_chapters)
    save_all_chapters(
        valid_chapters=valid_chapters,
        output_folder=output_folder,
        metadata=metadata,
        file_type=file_type,
    )

    logger.info(f"\nГотово! {total_chapters} розділів → {output_folder}/")
    logger.info(
        f"Книга: {metadata['title']} | ~{metadata['estimated_total_words']:,} слів"
    )


def pdf_to_markdown_pro(pdf_path: Path, output_folder):
    if not Path(output_folder).exists():
        Path(output_folder).mkdir(parents=True, exist_ok=True)
    file_type = BookFormat.PDF
    chunks = split_pdf(pdf_path=pdf_path, chunk_size=80)
    full_text = ""
    max_retries = 5
    for chunk in chunks:
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        types.Part.from_bytes(data=chunk, mime_type="application/pdf"),
                        "Convert this PDF into Markdown COMPLETELY, without omissions or abbreviations. "
                        "This is CRITICALLY IMPORTANT: process every page and every heading, even if the text is long. "
                        "Do not summarize, do not shorten, do not skip sections. "
                        "Use only the provided text. If you are not sure what exactly is written, leave it as the original. "
                        "Preserve the structure of the document: headings, lists, tables. "
                        "If you encounter a table, save it in Markdown table format. "
                        "If you encounter a graph, diagram, scheme, flowchart, or mind map, provide a text description "
                        "of up to 100 words: type, main elements and connections, main trend, or conclusion. "
                        "Return all descriptions and tables in the language of the original document, not in the language of this instruction. "
                        "Correct obvious OCR errors (broken words, extra spaces, incorrectly recognized characters). "
                        "Return only the full Markdown without explanations and without abbreviations.",
                    ],
                )
                full_text += response.text or ""
                break  # успіх — виходимо з retry
            except ClientError as e:
                logger.error(f"Спроба {attempt + 1} невдала: {e}")
                if attempt == 1:
                    raise  # дві спроби — пробрасуємо вгору
                time.sleep(60)
            except Exception as e:
                if "503" in str(e):
                    wait_time = 2**attempt * 5  # 1, 2, 4, 8... секунд
                    logger.error(f"Сервер перевантажений, чекаю {wait_time} секунд...")
                    time.sleep(wait_time)
                else:
                    raise
        time.sleep(4)
    word_count = len(full_text.split())
    valid_chapters = collect_chapters_from_text(content=full_text)
    total_chapters = len(valid_chapters)
    metadata = extract_pdf_metadata(pdf_path=pdf_path)
    save_all_chapters(
        valid_chapters=valid_chapters,
        output_folder=output_folder,
        metadata=metadata,
        file_type=file_type,
    )
    logger.info(f"\nГотово! {total_chapters} розділів → {output_folder}/")
    logger.info(f"Книга: {metadata['title']} | ~{word_count:,} слів")


def images_to_md(*, img_dict: dict[str, bytes], batch_size: int = 15) -> dict[str, str]:
    items = list(img_dict.items())
    all_results = {}

    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        parts = []
        index_to_name = {}
        for idx, (name, img_data) in enumerate(batch):
            parts.append(types.Part.from_bytes(data=img_data, mime_type="image/jpg"))
            index_to_name[idx] = name

        prompt_text = (
            "Carefully analyze EACH image separately by its sequence number. "
            "Do not mix up the images. "
            "For each, determine its type: table, graph, diagram/scheme, or decorative image. "
            "If it is a data table, return its content in Markdown table format. "
            "If it is a graph (bar, line, etc.), provide a description of up to 100 words: type, trend, key values. "
            "If it is a diagram or scheme (flowchart, architectural, mind map, etc.), "
            "provide a description of up to 100 words: what the scheme shows, main elements and connections, main conclusion. "
            "If it is a decorative image, photo, or illustration without data, return null. "
            "Return all descriptions and tables in the language of the original document, not in the language of this instruction. "
            'Format the response strictly as valid JSON: {"0": "...", "1": null, ...}. '
            "No explanations, no markdown formatting (no code blocks like ```json), only the raw JSON string."
        )
        parts.append(prompt_text)
        result = {}
        max_retries = 5

        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=parts,
                )
                text = response.text or ""
                result = json.loads(text.strip().strip("```json").strip("```"))
                break
            except ClientError as e:
                logger.error(f"Спроба {attempt + 1} невдала: {e}")
                if attempt == 1:
                    raise
                time.sleep(60)
            except json.JSONDecodeError as e:
                logger.error(f"Невалідний JSON від моделі: {e}")
                result = {}
                break
            except Exception as e:
                if "503" in str(e):
                    wait_time = 2**attempt * 5  # 1, 2, 4, 8... секунд
                    logger.error(f"Сервер перевантажений, чекаю {wait_time} секунд...")
                    time.sleep(wait_time)
                else:
                    raise

        all_results.update(
            {
                index_to_name[int(idx)]: desc
                for idx, desc in result.items()
                if desc is not None
            }
        )
        time.sleep(10)

    return all_results


def main():
    base_dir = Path(__file__).parent
    books_dir: Path = base_dir / "books"
    books_dir.mkdir(parents=True, exist_ok=True)
    output_dir: Path = base_dir / "output"
    for file in books_dir.iterdir():
        file_path = books_dir / file.name
        file_suffix = file.suffix
        try:
            match file_suffix:
                case ".epub":
                    epub_to_markdown_pro(file_path, output_dir / file.name)
                case ".pdf":
                    pdf_to_markdown_pro(
                        pdf_path=file_path, output_folder=output_dir / file.name
                    )
        except Exception as e:
            logger.error(f"Помилка при обробці {file.name}: {e}")
            continue


if __name__ == "__main__":
    main()
