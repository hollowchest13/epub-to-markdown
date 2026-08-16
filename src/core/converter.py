import logging
from collections.abc import Callable
from pathlib import Path

from google import genai

from parsers.epub import epub_to_markdown_pro
from parsers.md import md_parser_pro
from parsers.pdf import pdf_to_markdown_pro

logger = logging.getLogger(__name__)


def convert_to_md(
    files: list[Path],
    *,
    client: genai.Client,
    target_dir: Path,
    model: str,
    callback: Callable = lambda *args, **kwargs: None,
):
    for file in files:
        file_suffix = file.suffix
        output_dir: Path = target_dir / file.stem
        try:
            match file_suffix:
                case ".epub":
                    epub_to_markdown_pro(
                        epub_path=file,
                        output_dir=output_dir,
                        client=client,
                        model=model,
                        callback=callback,
                    )
                case ".pdf":
                    pdf_to_markdown_pro(
                        pdf_path=file,
                        output_dir=output_dir,
                        client=client,
                        model=model,
                        callback=callback,
                    )
                case ".md":
                    md_parser_pro(
                        md_path=file, output_dir=output_dir, callback=callback
                    )

                case _:
                    logger.warning("Skipping unsupported file: %s", file.name)
        except Exception:
            logger.exception("Processing error %s:", file.name)
            continue
