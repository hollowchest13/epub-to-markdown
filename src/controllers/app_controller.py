import threading
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog

from google import genai

from config.config import BASE_DIR, MODEL_VERSION
from core.converter import convert_to_md


class AppController:
    def __init__(
        self,
        *,
        api_client: genai.Client,
    ):
        self._gui_callback = lambda *args, **kwargs: None
        self._api_client = api_client

    @property
    def gui_callback(self):
        return self._gui_callback

    @gui_callback.setter
    def gui_callback(self, callback: Callable):
        self._gui_callback = callback

    def handle_start(self):
        files = filedialog.askopenfilenames(
            title="Select files",
            initialdir="/",
            filetypes=[
                ("Documents", "*.pdf *.epub *.md"),
                ("PDF files", "*.pdf"),
                ("EPUB files", "*.epub"),
                ("Markdown files", "*.md"),
            ],
        )
        if not files:
            return
        target_dir = BASE_DIR / "output"
        files = list(map(Path, files))
        self._run_long_process(
            lambda: convert_to_md(
                files=files,
                client=self._api_client,
                target_dir=target_dir,
                model=MODEL_VERSION,
                callback=self.gui_callback,
            )
        )

    def _run_long_process(self, func: Callable):
        threading.Thread(target=func, daemon=True).start()

    def handle_change_key(self):
        pass
