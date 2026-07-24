from pathlib import Path
from google import genai
from parsers.epub import epub_to_markdown_pro
from parsers.pdf import pdf_to_markdown_pro
from dotenv import load_dotenv
import os
import logging
from utils import collect_chapters_from_text
from storage.saver import save_all_chapters
from config import MODEL_VERSION
from cleaner import clean_text
from tkinter import filedialog


logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO)
    base_dir = Path(__file__).resolve().parent.parent.parent
    files = filedialog.askopenfilenames(
        title="Select files",
        initialdir="/",
        filetypes=[
            ("Documents", "*.pdf;*.epub;*.md"),
            ("PDF файли", "*.pdf"),
            ("EPUB файли", "*.epub"),
            ("Markdown файли", "*.md"),
        ],
    )
    load_dotenv()
    client = genai.Client(api_key=os.environ.get("GEMINI_API"))
    if not files:
        return
    files = list(map(Path, files))
    for file in files:
        file_suffix = file.suffix
        output_dir: Path = base_dir / "output" / file.stem
        try:
            match file_suffix:
                case ".epub":
                    epub_to_markdown_pro(
                        epub_path=file,
                        output_dir=output_dir,
                        client=client,
                        model=MODEL_VERSION,
                    )
                case ".pdf":
                    pdf_to_markdown_pro(
                        pdf_path=file,
                        output_dir=output_dir,
                        client=client,
                        model=MODEL_VERSION,
                    )
                case ".md":
                    text = file.read_text(encoding="utf-8")
                    text = clean_text(text=text)
                    valid_chapters = collect_chapters_from_text(
                        text=text, chapter_min_size=50
                    )
                    metadata = {}
                    save_all_chapters(
                        valid_chapters=valid_chapters,
                        output_dir=output_dir,
                        metadata=metadata,
                    )

                case _:
                    logger.warning("Skipping unsupported file: %s", file.name)
        except Exception:
            logger.exception("Processing error %s:", file.name)
            continue


if __name__ == "__main__":
    main()
