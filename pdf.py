import fitz
from pathlib import Path
from utils import build_metadata, clean_filename


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
