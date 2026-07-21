import logging
from pathlib import Path
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_PATTERNS = [
    (re.compile(r"<\?xml[^?]*\?>"), ""),
    (
        re.compile(
            r"<!--\s*Start of picture text\s*-->.*?<!--\s*End of picture text\s*-->",
            re.DOTALL,
        ),
        "",
    ),
    (re.compile(r"\([cp]\d+\.xhtml(?:#.*?)?\)"), ""),
    (re.compile(r"\(.*?\.html#filepos\d+\)"), ""),
    (re.compile(r"!\[.*?\]\(images/.*?\)"), ""),
    (re.compile(r"\[\d+\]"), ""),
    (re.compile(r"\(\#[a-z0-9]+-tbl-\d+\)"), ""),
    (re.compile(r"\n{3,}"), "\n\n"),
]


def clean_markdown(text):
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text.strip()


def cleaner(*, clean_dir: Path):

    for filepath in clean_dir.rglob("*.md"):
        content = filepath.read_text(encoding="utf-8")

        # 2. Очищення
        clean_content = clean_markdown(content)

        if content != clean_content:
            filepath.write_text(clean_content, encoding="utf-8")
            logger.info("Cleaned: %s", filepath.name)
