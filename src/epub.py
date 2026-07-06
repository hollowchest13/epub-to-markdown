from bs4 import BeautifulSoup
import ebooklib
from pathlib import Path
from utils import clean_filename, build_metadata, images_to_md
from ebooklib import epub
from google import genai
from utils import images_to_md,clean_markdown
from markdownify import markdownify as md
from models import BookFormat
from saver import save_all_chapters, save_epub_chapter
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_epub_metadata(*, book, epub_path):
    def first(key):
        values = book.get_metadata("DC", key)
        return values[0][0] if values else None

    def all_values(key):
        return (
            [v[0] for v in book.get_metadata("DC", key)]
            if book.get_metadata("DC", key)
            else []
        )

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
def collect_epub_chapters(*, book:epub.EpubBook,client:genai.Client,model:str) -> list[tuple[str, str]]:
    spine_ids = [item_id for item_id, _ in book.spine]
    ordered_items = [book.get_item_with_id(item_id) for item_id in spine_ids]
    img_dict = get_epub_images(book=book)
    image_descriptions = images_to_md(client=client,model=model,img_dict=img_dict) if img_dict else {}

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

def epub_to_markdown_pro(*,client:genai.Client,model:str,epub_path:Path, output_folder:Path):
    if not Path.exists(output_folder):
        Path.mkdir(output_folder, parents=True, exist_ok=True)
    file_type = BookFormat.EPUB

    book = epub.read_epub(epub_path)
    metadata = extract_epub_metadata(book=book, epub_path=epub_path)
    valid_chapters = collect_epub_chapters(book=book,client=client,model=model)
    total_chapters = len(valid_chapters)
    save_all_chapters(
        valid_chapters=valid_chapters,
        output_folder=output_folder,
        metadata=metadata,
        file_type=file_type,
        saver=save_epub_chapter
    )

    logger.info(f"\nГотово! {total_chapters} розділів → {output_folder}/")
    logger.info(
        f"Книга: {metadata['title']} | ~{metadata['estimated_total_words']:,} слів"
    )