from pathlib import Path
from google import genai
from parsers.epub import epub_to_markdown_pro
from parsers.pdf import pdf_to_markdown_pro
from dotenv import load_dotenv
import os
import logging
from cli.cleaner import cleaner
from config import MODEL_VERSION


logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO)
    base_dir = Path(__file__).resolve().parent.parent.parent
    books_dir: Path = base_dir / "books"
    books_dir.mkdir(parents=True, exist_ok=True)
    load_dotenv()
    client = genai.Client(api_key=os.environ.get("GEMINI_API"))
    for file in books_dir.iterdir():
        file_suffix = file.suffix
        output_dir: Path = base_dir / "output" / file.stem
        try:
            match file_suffix:
                case ".epub":
                    epub_to_markdown_pro(
                        epub_path=file,
                        output_folder=output_dir,
                        client=client,
                        model=MODEL_VERSION,
                    )
                case ".pdf":
                    pdf_to_markdown_pro(
                        pdf_path=file,
                        output_folder=output_dir,
                        client=client,
                        model=MODEL_VERSION,
                        only_local=True,
                    )
                case _:
                    logger.warning("Skipping unsupported file: %s", file.name)
        except Exception:
            logger.exception("Processing error %s:", file.name)
            continue
    try:
        clean_dir: Path = base_dir / "output"
        cleaner(clean_dir=clean_dir)
    except Exception:
        logger.exception("Clean exception")


if __name__ == "__main__":
    main()
