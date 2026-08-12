import logging
from collections.abc import Callable

from core.cleaner import clean_text
from core.utils import Path, collect_chapters_from_text, genai
from parsers.epub import epub_to_markdown_pro
from parsers.pdf import pdf_to_markdown_pro
from storage.saver import save_all_chapters

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
        output_dir: Path = target_dir / "output" / file.stem
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
