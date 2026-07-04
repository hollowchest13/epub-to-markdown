from pathlib import Path
from datetime import datetime
import hashlib
import re


def clean_filename(*, file_path: Path):
    # Прибираємо розширення (.pdf, .epub)
    name = file_path.stem
    # Замінюємо нижнє підкреслення на пробіли
    return name.replace("_", " ").replace("-", " ").title()


def build_metadata(*, source_file: Path, extra: dict) -> dict:
    file_size_bytes = source_file.stat().st_size

    base = {
        # --- Технічні дані файлу ---
        "source_file": source_file.name,
        "file_type": source_file.suffix.lstrip(".").lower(),
        "file_size_bytes": file_size_bytes,
        "file_hash_sha256": get_file_hash(source_file),
        "file_size_kb": round(file_size_bytes / 1024, 2),
        # --- Конвертація ---
        "converted_date": datetime.now().strftime("%Y-%m-%d"),
        "converted_at": datetime.now().isoformat(),
    }

    return base | extra  # merge двох словників


def get_file_hash(file_path, algorithm="sha256"):
    h = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_markdown(text):
    text = re.sub(r"<\?xml[^?]*\?>", "", text)
    text = re.sub(r"xml version=['\"].*?['\"]", "", text)
    text = re.sub(r"encoding=['\"]utf-8['\"][?]?", "", text)
    text = re.sub(r"\([cp]\d+\.xhtml(?:#.*?)?\)", "", text)
    text = re.sub(r"\(.*?\.html#filepos\d+\)", "", text)
    text = re.sub(r"!\[.*?\]\(images/.*?\)", "", text)
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
