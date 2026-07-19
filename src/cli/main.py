from pathlib import Path
from google import genai
from parsers.epub import epub_to_markdown_pro
from parsers.pdf import pdf_to_markdown_pro
from dotenv import load_dotenv
import os
import logging
from config import MODEL_VERSION


logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO)
    base_dir = Path(__file__).parent
    books_dir: Path = base_dir / "books"
    books_dir.mkdir(parents=True, exist_ok=True)
    output_dir: Path = base_dir / "output"
    load_dotenv()
    client = genai.Client(api_key=os.environ.get("GEMINI_API"))

    for file in books_dir.iterdir():
        file_path = books_dir / file.name
        file_suffix = file.suffix
        try:
            match file_suffix:
                case ".epub":
                    epub_to_markdown_pro(
                        epub_path=file_path,
                        output_folder=output_dir / file.name,
                        client=client,
                        model=MODEL_VERSION,
                    )
                case ".pdf":
                    pdf_to_markdown_pro(
                        pdf_path=file_path,
                        output_folder=output_dir / file.name,
                        client=client,
                        model=MODEL_VERSION,
                    )
        except Exception as e:
            logger.error("Processing error %s: %s", file.name,e,exc_info=True)
            continue


if __name__ == "__main__":
    main()
