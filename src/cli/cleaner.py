import logging
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
    (re.compile(r"<[^>]+>"), ""),  # HTML теги типу <span id="...">
    (re.compile(r"\n{3,}"), "\n\n"),
]


def clean_text(text):
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text.strip()
