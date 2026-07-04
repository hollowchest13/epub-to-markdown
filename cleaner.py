import logging
from utils import clean_markdown
import re
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UA_PATTERN = re.compile(r"[ієїґІЇЄҐ]")


def check_ukrainian_language(filepath, text):
    """Перевіряє наявність українських літер у тексті."""
    if UA_PATTERN.search(text):
        print(f"[UKR] Знайдено українську мову у: {filepath.name}")
    else:
        print(f"[!] УВАГА: Української мови не виявлено у: {filepath.name}")


def cleaner():
    root_folder = Path("/home/hollowchest13/Завантажене/result")
    root = Path(root_folder)

    for filepath in root.rglob("*.md"):
        content = filepath.read_text(encoding="utf-8")

        # 1. Перевірка на мову перед очищенням
        check_ukrainian_language(filepath, content)

        # 2. Очищення
        clean_content = clean_markdown(content)

        if content != clean_content:
            filepath.write_text(clean_content, encoding="utf-8")
            print(f"Очищено: {filepath.name}")


if __name__ == "__main__":
    cleaner()
