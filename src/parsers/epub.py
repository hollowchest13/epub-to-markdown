from bs4 import BeautifulSoup
import ebooklib
from pathlib import Path
from utils import clean_filename, build_metadata, images_to_md, clean_markdown
from ebooklib import epub
from google import genai
from markdownify import markdownify as md
from storage.saver import save_all_chapters, save_epub_chapter
from typing import Any
from config import CHAPTER_MIN_SIZE, IMG_CHUNK_SIZE
from models import BookFormat
import logging

logger = logging.getLogger(__name__)


def extract_epub_metadata(*, book:epub.EpubBook, epub_path:Path):
    def first(key:str):
        values:Any = book.get_metadata("DC", key)
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
            "description": first("description"),
            "subjects": all_values("subject"),
            "total_spine_items": total_spine_items,
            "estimated_total_words": total_words,
            "file_type": BookFormat.EPUB.value,
        },
    )

def _extract_chapter_text(
    item, image_descriptions: dict, strip_nav: bool = True
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

    soup = replace_images(soup, image_descriptions)
    text = md(str(soup))
    text = clean_markdown(text)
    return text, soup


def collect_epub_chapters(
    *, book: epub.EpubBook, client: genai.Client, model: str, chapter_min_size: int
) -> list[tuple[str, str]]:
    spine_ids = [item_id for item_id, _ in book.spine]
    # Використовуємо spine_ids, щоб отримати елементи
    ordered_items = [book.get_item_with_id(item_id) for item_id in spine_ids]
    img_dict = get_epub_images(book=book)

    try:
        image_descriptions = (
            images_to_md(
                client=client, model=model, img_dict=img_dict, batch_size=IMG_CHUNK_SIZE
            )
            if img_dict
            else {}
        )
    except Exception as e:
        logger.error("Failed to generate image descriptions; continuing without them %s",e,exc_info=True)
        image_descriptions = {}

    valid_chapters = []

    # Main cycle
    for item in ordered_items:
        if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        try:
            text, soup = _extract_chapter_text(item, image_descriptions, strip_nav=True)

            if len(text) > chapter_min_size:
                header = soup.find(["h1", "h2", "h3"])
                header_text = header.get_text().strip() if header else ""
                chapter_name = (
                    header_text
                    if header_text
                    else f"Chapter {len(valid_chapters) + 1}"
                )
                valid_chapters.append((chapter_name, text))
        except Exception as e:
            logger.error("Error processing item during main loop %s",e,exc_info=True)

    # Fallback
    if not valid_chapters:
        all_text = []
        for item in ordered_items:
            if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
                continue
            try:
                text, _ = _extract_chapter_text(item, image_descriptions, strip_nav=True)
                if text.strip():
                    all_text.append(text)
            except Exception as e:
                logger.error("Error processing item during fallback loop %s",e,exc_info=True)

        return [("Full content", "\n\n".join(all_text))]

    return valid_chapters


def get_epub_images(*, book) -> dict[str, bytes]:
    images: dict = {}
    for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        img_bytes = item.get_content()
        img_name = item.get_name()
        images[img_name] = img_bytes
    return images


def replace_images(soup, image_descriptions: dict[str, str]):
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


def epub_to_markdown_pro(
    *, client: genai.Client, model: str, epub_path: Path, output_folder: Path
):
    book = epub.read_epub(epub_path)
    metadata = extract_epub_metadata(book=book, epub_path=epub_path)
    valid_chapters = collect_epub_chapters(
        book=book, client=client, model=model, chapter_min_size=CHAPTER_MIN_SIZE
    )
    total_chapters = len(valid_chapters)
    save_all_chapters(
        valid_chapters=valid_chapters,
        output_folder=output_folder,
        metadata=metadata,
        saver=save_epub_chapter,
    )

    logger.info("Completed! %s chapters → %s/",total_chapters,output_folder)
    logger.info(
        "Book: %s | ~%s words",metadata['title'],metadata['estimated_total_words']
    )
