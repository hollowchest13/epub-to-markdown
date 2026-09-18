from collections.abc import Callable
from pathlib import Path

from google import genai

from config.config_manager import ConfigManager


class BaseParser:
    def __init__(self, config_manager: ConfigManager):
        self._config_manager = config_manager
        self._prompt_dict = config_manager.get_prompt_dict()

    def to_markdown(
        self,
        *,
        file_path: Path,
        output_dir: Path,
        client: genai.Client | None = None,
        on_rate_limit: Callable = lambda *args, **kwargs: None,
        callback: Callable = lambda *args, **kwargs: None,
    ):
        pass
