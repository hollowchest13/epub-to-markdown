import threading
from collections.abc import Callable
from pathlib import Path

from google import genai
from google.genai import types

from config.config_manager import ConfigManager
from controllers.base_controller import BaseController
from core.converter import convert_to_md


class AppController(BaseController):
    def __init__(self, *, config_manager: ConfigManager):
        super().__init__()
        self._rate_limit_event = threading.Event()
        self._config_manager = config_manager

    @property
    def gui_callback(self):
        return self._gui_callback

    @gui_callback.setter
    def gui_callback(self, callback: Callable):
        self._gui_callback = callback

    def convert_files(
        self,
        *,
        files: tuple[str, ...],
        api_key: str | None,
        on_done: Callable | None = None,
    ):
        if not api_key:
            return
        self._rate_limit_event.clear()
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=180000,
            ),
        )
        target_dir = self._config_manager.output_dir
        file_list = list(map(Path, files))
        self._run_long_process(
            lambda: convert_to_md(
                files=file_list,
                client=client,
                target_dir=target_dir,
                config_manager=self._config_manager,
                callback=self.gui_callback,
                on_rate_limit=self._on_rate_limit,
            ),
            on_done=on_done,
        )

    def _on_rate_limit(self):
        if not self._rate_limit_event.is_set():
            self._rate_limit_event.set()
            msg = ("API rate limit exceeded. Falling back to local processing...",)
            self._emit(event="show_msg", msg=msg)

    def _run_long_process(self, func: Callable, on_done: Callable | None = None):
        def wrapper():
            try:
                func()
            finally:
                if on_done:
                    on_done()

        threading.Thread(target=wrapper, daemon=True).start()

    def get_api_key(self):
        return self._config_manager.get_api_key()
