from enum import StrEnum

from pydantic import BaseModel


class PromptType(StrEnum):
    IMAGE_PROMPT = "image_prompt"
    PDF_PROMPT = "pdf_prompt"


class BookFormat(StrEnum):
    EPUB = ".epub"
    PDF = ".pdf"
    MD = ".md"


class ImageAnalysisResponse(BaseModel):
    results: list[str | None]
