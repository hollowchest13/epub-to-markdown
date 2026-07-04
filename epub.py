from bs4 import BeautifulSoup
import ebooklib
from pathlib import Path
from utils import clean_filename, build_metadata


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
