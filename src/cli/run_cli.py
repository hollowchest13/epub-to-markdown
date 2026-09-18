import argparse
import logging
from collections.abc import Callable
from pathlib import Path

from google import genai

from config.config import BASE_DIR
from config.config_manager import ConfigManager
from core.converter import convert_to_md

logger = logging.getLogger(__name__)


def run_cli(config_manager: ConfigManager):
    args = _parse_arguments()
    base_dir = BASE_DIR

    if args.set_key:
        _handle_set_key(config_manager)
        return
    gemini_api_key = config_manager.get_api_key()
    try:
        if not gemini_api_key:
            try:
                gemini_api_key = _get_entered_key(validator=config_manager.validate_key)
                config_manager.save_and_activate(gemini_api_key)
            except (ConnectionError, TimeoutError) as e:
                print(f"\nNetwork error: {e}. Exiting.")
                return
        files = _get_files_cli(args.dir)
    except SystemExit as e:
        print(f"\n{e}")
        return

    if not files:
        print("The directory is empty.")
        return

    client = genai.Client(api_key=gemini_api_key)
    convert_to_md(
        files,
        config_manager=config_manager,
        client=client,
        target_dir=base_dir,
    )


def _handle_set_key(config_manager: ConfigManager) -> None:
    print("Updating Gemini API key...")
    try:
        new_key = _get_entered_key(validator=config_manager.validate_key)
        config_manager.save_and_activate(new_key)
        print("API key successfully updated!")
    except (ConnectionError, TimeoutError) as e:
        print(f"\nNetwork error while validating key: {e}")


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Console utility for converting files to Markdown using Gemini."
    )
    parser.add_argument(
        "-d", "--dir", type=Path, default=None, help="Path to the file folder"
    )
    parser.add_argument(
        "-k", "--set-key", action="store_true", help="Set or update your Gemini API key"
    )
    return parser.parse_args()


def _get_entered_key(validator: Callable[[str], str]) -> str:
    while True:
        entered_key = input("Please input your Gemini API key: ").strip()

        if entered_key.lower() == "q":
            raise SystemExit("The program has been stopped by the user.")

        if not entered_key:
            print("Key can't be empty. Please try again.\n")
            continue

        try:
            return validator(entered_key)
        except (ConnectionError, TimeoutError) as e:
            logger.error("Network error: %s", e)
            print(
                "Network error. Please check your internet connection and try again.\n"
            )
            raise
        except ValueError as e:
            print(f"\nInvalid key: {e}")
            print("Please try again.\n")


def _get_files_cli(book_dir: Path | None) -> list[Path]:
    if book_dir is not None:
        if not book_dir.is_dir():
            raise SystemExit(f"Error: '{book_dir}' is not a valid directory.")

        files = [f for f in book_dir.iterdir() if f.is_file()]
        if not files:
            raise SystemExit(f"Error: The directory '{book_dir}' is empty.")
        return files

    while True:
        user_input = input("Input folder path (or 'q' to quit): ").strip()
        if user_input.lower() == "q":
            raise SystemExit("The program has been stopped by the user.")

        book_dir = Path(user_input).expanduser()

        if book_dir.is_dir():
            files = [f for f in book_dir.iterdir() if f.is_file()]
            if not files:
                print(f"The directory '{book_dir}' is empty. Try another one.")
                continue
            return files

        print(f"Error: '{book_dir}' is not a valid directory. Try again.")
