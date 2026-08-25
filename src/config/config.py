import sys
from pathlib import Path

import StrEnum

IMG_CHUNK_SIZE = 15
API_DELAY = 6
OUT_OF_LIMIT_DELAY = 60
CHAPTER_MIN_SIZE = 200
MAX_API_RETRIES = 5
MIN_CHUNK_LENGTH = 50
MODEL_VERSION = "gemini-3.1-flash-lite"

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    print(BASE_DIR)

DEFAULT_SETTINGS = {"mode": "gui"}
PROMPTS_JSON_PATH = BASE_DIR / "prompts.json"


class PromptType(StrEnum):
    IMAGE_PROMPT = "image_prompt"
    PDF_PROMPT = "pdf_prompt"


DEFAULT_PROMPTS = {
    PromptType.IMAGE_PROMPT: (
        "Task: Analyze EACH provided image separately, in the exact order they are given. "
        "Do not skip, merge, or reorder images. "
        "Classify and process each image according to these rules:\n"
        "1. DATA TABLE: Convert its full content strictly into Markdown table format.\n"
        "2. GRAPH (bar, line, pie, etc.): Provide a concise description (up to 100 words) specifying its type, main trend, and key values.\n"
        "3. DIAGRAM/SCHEME (flowchart, architecture, mind map): Provide a description (up to 100 words) explaining what it shows, its main elements, connections, and key conclusion.\n"
        "4. FORMULA/EQUATION: Convert the formula strictly into LaTeX format (e.g., using $...$ or $$...$$).\n"
        "5. DECORATIVE IMAGE (photo, illustration, spacer without data): Return exactly null.\n\n"
        "IMPORTANT: There are exactly {batch_size} images in this request. "
        "Return a JSON array with EXACTLY {batch_size} elements, one per image, "
        "in the same order as the images were provided. Never omit an element — "
        "use null for decorative images instead of skipping them.\n\n"
        "Constraints:\n"
        "- Language: Return all text, descriptions, and tables in the original document's language.\n"
        "- Output Format: Return ONLY a single valid raw JSON array, exactly like this: "
        '["markdown_table_or_description", null, "$E=mc^2$"].\n'
        "- CRITICAL: Do not include any introductory text, explanations, notes, or markdown code block fences (like ```json or ```). Only the raw JSON array."
    ),
    PromptType.PDF_PROMPT: (
        """Task: Extract the structural and textual content from the provided material and represent it in Markdown format for personal analysis and indexing.
        Guidelines:
        Process the provided text fragment in detail, maintaining the original structure, headings, and hierarchy.
        Use ONLY the provided source material. Ensure high fidelity to the original text; if a word is unclear, maintain its visual representation.
        TABLES: Format all data tables into standard Markdown tables.
        VISUALS: Provide a concise analytical description of any graphs, diagrams, or schemes, focusing on their main elements and logical connections (up to 100 words per item).
        LANGUAGE: Keep the output strictly in the original document's language.
        DATA CLEANING: Fix minor OCR artifacts (e.g., broken words, unnecessary line breaks) to improve readability.
        OUTPUT: Return the output as raw Markdown content. Focus on accuracy and technical formatting."""
    ),
}
