import logging
from pathlib import Path
from tkinter import filedialog

from google import genai

from config.config import BASE_DIR, MODEL_VERSION
from config.config_manager import ConfigManager
from core.converter import convert_to_md

logger = logging.getLogger(__name__)


def run_cli(config_manager:ConfigManager):
    logging.basicConfig(level=logging.INFO)
    base_dir = BASE_DIR
    gemini_api_key = config_manager.get_api_key()
    files=_get_files_cli()
    client = genai.Client(api_key=gemini_api_key)
    if not files:
        return
    convert_to_md(files, client=client, model=MODEL_VERSION, target_dir=base_dir)

def _get_files_cli()->list[Path]:
    while True:
        book_dir=Path(input("Input folder path: "))
        if book_dir.is_dir():
            return [f for f in book_dir.iterdir() if f.is_file()]
            
