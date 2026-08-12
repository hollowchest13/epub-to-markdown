import threading
from collections.abc import Callable
from pathlib import Path

from google import genai

from config.config import BASE_DIR, MODEL_VERSION
from config.config_manager import ConfigManager
from controllers.base_controller import BaseController
from core.converter import convert_to_md


class AppController(BaseController):
    def __init__(self, *, config_manager: ConfigManager):
        super().__init__()

        self.config_manager = config_manager

    @property
    def gui_callback(self):
        return self._gui_callback

    @gui_callback.setter
    def gui_callback(self, callback: Callable):
        self._gui_callback = callback

    def convert_files(self, *, files: tuple[str, ...], api_key: str | None):
        if not api_key:
            return
        client = genai.Client(api_key=api_key)
        target_dir = BASE_DIR / "output"
        file_list = list(map(Path, files))
        self._run_long_process(
            lambda: convert_to_md(
                files=file_list,
                client=client,
                target_dir=target_dir,
                model=MODEL_VERSION,
                callback=self.gui_callback,
            )
        )

    def _run_long_process(self, func: Callable):
        threading.Thread(target=func, daemon=True).start()

    def get_api_key(self):
        return self.config_manager.get_api_key()
