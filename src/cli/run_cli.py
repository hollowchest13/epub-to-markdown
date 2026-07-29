import logging
from pathlib import Path
from tkinter import filedialog

from google import genai

from cleaner import clean_text
from config.config_manager import ConfigManager
from config.config import BASE_DIR, MODEL_VERSION
from parsers.epub import epub_to_markdown_pro
from parsers.pdf import pdf_to_markdown_pro
from storage.saver import save_all_chapters
from utils import collect_chapters_from_text

logger = logging.getLogger(__name__)


def run_cli():
    logging.basicConfig(level=logging.INFO)
    base_dir = BASE_DIR

    config_manager = ConfigManager(base_dir=base_dir)
    gemini_api_key = config_manager.get_api_key()

    files = filedialog.askopenfilenames(
        title="Select files",
        initialdir="/",
        filetypes=[
            ("Documents", "*.pdf* .epub *.md"),
            ("PDF files", "*.pdf"),
            ("EPUB files", "*.epub"),
            ("Markdown files", "*.md"),
        ],
    )
    client = genai.Client(api_key=gemini_api_key)
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
    run_cli()
    input("Press Enter to exit...")
