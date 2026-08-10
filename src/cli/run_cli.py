import argparse
import logging
from pathlib import Path

from google import genai

from config.config import BASE_DIR, MODEL_VERSION
from config.config_manager import ConfigManager
from core.converter import convert_to_md

logger = logging.getLogger(__name__)


def run_cli(config_manager: ConfigManager):
    base_dir = BASE_DIR
    gemini_api_key = config_manager.get_api_key()
    try:
        files = _get_files_cli()
    except SystemExit as e:
        print(f"\n{e}")
        return

    if not files:
        print("The directory is empty.")
        return

    client = genai.Client(api_key=gemini_api_key)
    convert_to_md(files, client=client, model=MODEL_VERSION, target_dir=base_dir)


def _get_files_cli() -> list[Path]:
    parser = argparse.ArgumentParser(
        description="Get a list of files from a given folder."
    )
    parser.add_argument(
        "-d", "--dir", type=Path, default=None, help="Path to the file folder"
    )
    args = parser.parse_args()

    book_dir = args.dir
    if book_dir is not None:
        if not book_dir.is_dir():
            parser.error(f"Error: '{book_dir}' is not a valid directory.")
        return [f for f in book_dir.iterdir() if f.is_file()]

    while True:
        user_input = input("Input folder path (or 'q' to quit): ").strip()
        if user_input.lower() == "q":
            raise SystemExit("The program has been stopped by the user.")

        book_dir = Path(user_input)

        if book_dir.is_dir():
            return [f for f in book_dir.iterdir() if f.is_file()]

        logger.warning(f"Error: '{book_dir}' is not a valid directory. Try again.")
