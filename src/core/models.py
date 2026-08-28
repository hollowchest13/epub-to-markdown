from enum import StrEnum


class PromptType(StrEnum):
    IMAGE_PROMPT = "image_prompt"
    PDF_PROMPT = "pdf_prompt"


class BookFormat(StrEnum):
    EPUB = ".epub"
    PDF = ".pdf"
    MD = ".md"
