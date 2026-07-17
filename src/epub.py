from bs4 import BeautifulSoup
import ebooklib
from pathlib import Path
from src.utils import clean_filename, build_metadata, images_to_md, clean_markdown
from ebooklib import epub
from google import genai
from markdownify import markdownify as md
from src.models import BookFormat
from src.saver import save_all_chapters, save_epub_chapter
from src.config import CHAPTER_MIN_SIZE, IMG_CHUNK_SIZE
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_epub_metadata(*, book, epub_path):
    def first(key):
        values = book.get_metadata("DC", key)
        # Перевіряємо: чи є список, чи є в ньому перший елемент, чи є в елементі значення
        if values and isinstance(values[0], (list, tuple)) and len(values[0]) > 0:
            return values[0][0]

        # Якщо це просто рядок (інколи metadata повертає (value,))
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

    # Підрахунок сторінок (кількість spine-документів як приблизна оцінка)
    spine_ids = [item_id for item_id, _ in book.spine]
    total_spine_items = len(spine_ids)

    # Підрахунок слів по всьому тексту
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
        },
    )


def collect_epub_chapters(
    *, book: epub.EpubBook, client: genai.Client, model: str, chapter_min_size: int
) -> list[tuple[str, str]]:
    spine_ids = [item_id for item_id, _ in book.spine]
    # Використовуємо spine_ids, щоб отримати елементи
    ordered_items = [book.get_item_with_id(item_id) for item_id in spine_ids]
    img_dict = get_epub_images(book=book)
    image_descriptions = (
        images_to_md(
            client=client, model=model, img_dict=img_dict, batch_size=IMG_CHUNK_SIZE
        )
        if img_dict
        else {}
    )

    valid_chapters = []

    # Головний цикл
    for item in ordered_items:
        if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        try:
            soup = BeautifulSoup(item.get_content(), "html.parser")
            for tag in soup.find_all(["script", "style", "nav"]):
                tag.decompose()
            soup = replace_images(soup, image_descriptions)
            text = md(str(soup))
            text = clean_markdown(text)

            if len(text) > chapter_min_size:
                header = soup.find(["h1", "h2", "h3"])
                chapter_name = (
                    header.get_text().strip()
                    if header
                    else f"Chapter {len(valid_chapters) + 1}"
                )
                valid_chapters.append((chapter_name, text))
        except Exception as e:
            logger.error(f"Помилка обробки item: {e}")

    # Блок "запобіжник": якщо нічого не знайдено
    if not valid_chapters:
        all_text = []
        for item in ordered_items:
            if item and item.get_type() == ebooklib.ITEM_DOCUMENT:
                # Очищуємо текст так само, як і в основному циклі
                soup = BeautifulSoup(item.get_content(), "html.parser")
                text = md(str(soup))
                text = clean_markdown(text)
                all_text.append(text)

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
    # Нормалізуємо ключі описів — лише ім'я файлу
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
    if not Path.exists(output_folder):
        Path.mkdir(output_folder, parents=True, exist_ok=True)
    file_type = BookFormat.EPUB
    try:
        book = epub.read_epub(epub_path)
    except Exception as e:
        logger.error(f"Помилка в читання: {e}")
        raise
    try:
        metadata = extract_epub_metadata(book=book, epub_path=epub_path)
    except Exception as e:
        logger.error(f"Помилка в extract_epub_metadata: {e}")
        raise
    try:
        valid_chapters = collect_epub_chapters(
            book=book, client=client, model=model, chapter_min_size=CHAPTER_MIN_SIZE
        )
    except Exception as e:
        logger.error(f"Помилка в collect_epub_chapters: {e}")
        raise
    total_chapters = len(valid_chapters)

    save_all_chapters(
        valid_chapters=valid_chapters,
        output_folder=output_folder,
        metadata=metadata,
        file_type=file_type,
        saver=save_epub_chapter,
    )

    logger.info(f"\nГотово! {total_chapters} розділів → {output_folder}/")
    logger.info(
        f"Книга: {metadata['title']} | ~{metadata['estimated_total_words']:,} слів"
    )
