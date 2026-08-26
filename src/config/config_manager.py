import logging
import os
from pathlib import Path

from dotenv import set_key
from google import genai
from google.genai.errors import APIError

from config.config import PromptType
from core.utils import get_json_data

logger = logging.getLogger(__name__)


class ConfigManager:
    def __init__(
        self,
        base_dir: Path,
        prompts_path: Path,
        default_prompts: dict[PromptType, str],
        model: str,
        api_key_name="GEMINI_API_KEY",
        filename=".env",
    ):

        self._base_dir = base_dir
        self._env_path = self._base_dir / filename
        self._model = model
        self._api_key_name = api_key_name
        self._prompts_path = prompts_path
        self._default_prompts = default_prompts

    @property
    def output_dir(self) -> Path:
        return self._base_dir / "output"

    @property
    def model(self) -> str:
        return self._model

    def get_prompt_dict(self) -> dict[PromptType, str]:
        raw_data = get_json_data(
            json_file=self._prompts_path,
            default_data={str(k): v for k, v in self._default_prompts.items()},
        )
        return {PromptType(k): v for k, v in raw_data.items()}

    def get_api_key(self) -> str | None:
        """Main method: checks the key, prompts for input if necessary, and saves."""
        if not self._env_path.exists():
            return None
        else:
            api_key = self._read_key_from_file()
            if api_key:
                os.environ[self._api_key_name] = api_key
                return api_key

    def validate_key(self, api_key: str) -> str:
        """
        Verify the key with a real request to Gemini.
        Return api_key:str if is valid or raise ValueError if not.
        Also raises ConnectionError, TimeoutError if bad internet connection.
        """
        try:
            client = genai.Client(api_key=api_key)
            client.models.generate_content(
                model=self.model,
                contents="Test",
            )
            return api_key
        except APIError:
            logger.warning("Invalid API key")
            raise ValueError("Invalid API key")
        except (ConnectionError, TimeoutError):
            logger.exception("Internet connection error. Check your connection.")
            raise ConnectionError("Internet connection error. Check your connection.")
        except Exception:
            logger.exception("Unexpected error during API key validation.")
            raise

    def _save_key_to_file(self, api_key: str):
        set_key(self._env_path, self._api_key_name, api_key)

    def _read_key_from_file(self) -> str:
        """Reads the key from the .env file."""
        try:
            with open(self._env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith(f"{self._api_key_name}="):
                        return line.split("=", 1)[1].strip().strip("\"'")
        except OSError as e:
            logger.warning(
                "Could not read configuration file. %s: %s", self._env_path, e
            )
        return ""

    def save_and_activate(self, api_key: str):
        self._save_key_to_file(api_key)
        os.environ[self._api_key_name] = api_key
