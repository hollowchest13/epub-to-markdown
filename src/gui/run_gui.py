import logging
from pathlib import Path
from tkinter import filedialog

from google import genai

from config.config import BASE_DIR, MODEL_VERSION
from config.config_manager import ConfigManager
from core.converter import convert_to_md
from gui.app import App

logger = logging.getLogger(__name__)


def run_gui(config_manager: ConfigManager):
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
    convert_to_md(files,client=client,target_dir=base_dir,model=MODEL_VERSION)
