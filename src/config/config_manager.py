import json
import logging
import os
from pathlib import Path

from dotenv import set_key
from google import genai
from google.genai.errors import APIError

from config.config import DEFAULT_SETTINGS, MODEL_VERSION

logger = logging.getLogger(__name__)


def get_settings(
    settings_json: Path, default_settings: dict = DEFAULT_SETTINGS
) -> dict:
    try:
        if not settings_json.exists():
            settings_json.write_text(
                json.dumps(default_settings, indent=4, ensure_ascii=False),
                encoding="utf-8",
            )
        return json.loads(settings_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not read settings file: %s", e)
    return default_settings


class ConfigManager:
    def __init__(self, base_dir: Path, filename=".env", model: str = MODEL_VERSION):

        self.base_dir = base_dir
        self.env_path = self.base_dir / filename
        self.model = model
        self.api_key_name = "GEMINI_API"

    def get_api_key(self) -> str | None:
        """Main method: checks the key, prompts for input if necessary, and saves."""
        if not self.env_path.exists():
            return None
        else:
            api_key = self._read_key_from_file()
            if api_key:
                os.environ[self.api_key_name] = api_key
                return api_key if self._validate_key(api_key=api_key) else None

    def _validate_key(self, api_key: str) -> str:
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
        set_key(self.env_path, self.api_key_name, api_key)

    def _read_key_from_file(self) -> str:
        """Reads the key from the .env file."""
        try:
            with open(self.env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith(f"{self.api_key_name}="):
                        return line.split("=", 1)[1].strip()
        except OSError as e:
            logger.warning(
                "Could not read configuration file. %s: %s", self.env_path, e
            )
        return ""

    def save_and_activate(self, api_key: str):
        api_key = self._validate_key(api_key)
        self._save_key_to_file(api_key)
        os.environ[self.api_key_name] = api_key
