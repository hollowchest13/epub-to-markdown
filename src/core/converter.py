import logging
from collections.abc import Callable
from pathlib import Path

from google import genai

from config.config_manager import ConfigManager
from parsers import EpubParser, MdParser, PdfParser

logger = logging.getLogger(__name__)


def convert_to_md(
    files: list[Path],
    *,
    client: genai.Client,
    config_manager: ConfigManager,
    target_dir: Path,
    callback: Callable = lambda *args, **kwargs: None,
    on_rate_limit: Callable = lambda *args, **kwargs: None,
):
    epub_parser = None
    pdf_parser = None
    md_parser = None
    parser = None
    for file in files:
        file_suffix = file.suffix
        output_dir: Path = target_dir / file.stem
        try:
            match file_suffix:
                case ".epub":
                    if not epub_parser:
                        epub_parser = EpubParser(config_manager=config_manager)
                    parser = epub_parser

                case ".pdf":
                    if not pdf_parser:
                        pdf_parser = PdfParser(config_manager=config_manager)
                    parser = pdf_parser

                case ".md":
                    if not md_parser:
                        md_parser = MdParser(config_manager=config_manager)
                    parser = md_parser
                case _:
                    logger.warning("Skipping unsupported file: %s", file.name)

            if parser:
                parser.to_markdown(
                    file_path=file,
                    output_dir=output_dir,
                    client=client,
                    callback=callback,
                    on_rate_limit=on_rate_limit,
                )
        except Exception:
            logger.exception("Processing error %s:", file.name)
            continue
