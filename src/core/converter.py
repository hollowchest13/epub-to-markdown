import logging
from collections.abc import Callable
from pathlib import Path

from google import genai

from config.config import PromptType
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
    prompt_dict: dict,
    callback: Callable = lambda *args, **kwargs: None,
    on_rate_limit: Callable | None = None,
):
    for file in files:
        file_suffix = file.suffix
        output_dir: Path = target_dir / file.stem
        try:
            match file_suffix:
                case ".epub":
                    prompt_text = prompt_dict[PromptType.IMAGE_PROMPT]
                    epub_to_markdown_pro(
                        epub_path=file,
                        output_dir=output_dir,
                        client=client,
                        model=model,
                        prompt_text=prompt_text,
                        callback=callback,
                        on_rate_limit=on_rate_limit,
                    )
                case ".pdf":
                    prompt_text = prompt_dict[PromptType.PDF_PROMPT]
                    pdf_to_markdown_pro(
                        pdf_path=file,
                        output_dir=output_dir,
                        client=client,
                        prompt_text=prompt_text,
                        model=model,
                        callback=callback,
                        on_rate_limit=on_rate_limit,
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
