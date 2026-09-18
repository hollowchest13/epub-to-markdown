import logging
import os
from pathlib import Path
from typing import Any

import tomllib
from dotenv import dotenv_values, set_key
from google import genai
from google.genai.errors import APIError

from config.models import ConfigKey
from core.models import PromptType
from core.utils import get_json_data
from errors.network_errors import NetworkError

logger = logging.getLogger(__name__)


class ConfigManager:
    def __init__(
        self,
        base_dir: Path,
        api_key_name="GEMINI_API_KEY",
        filename=".env",
    ):

        self._base_dir = base_dir
        self._env_path = self._base_dir / filename
        self._api_key_name = api_key_name
        self._config_toml = self._base_dir / "pyproject.toml"
        self._settings_json = self._base_dir / "settings.json"
        self._default_settings: dict[str, Any] = {
            ConfigKey.MODE: "api",
            ConfigKey.IMG_CHUNK_SIZE: 15,
            ConfigKey.API_DELAY: 6,
            ConfigKey.OUT_OF_LIMIT_DELAY: 60,
            ConfigKey.CHAPTER_MIN_SIZE: 200,
            ConfigKey.MAX_API_RETRIES: 5,
            ConfigKey.MIN_CHUNK_LENGTH: 50,
            ConfigKey.MODEL_VERSION: "gemma-4-26B-A4B-it",
        }

    @property
    def output_dir(self) -> Path:
        return self._ensure_dir("output")

    @property
    def uploads_dir(self) -> Path:
        return self._ensure_dir("uploads")

    @property
    def prompts_path(self) -> Path:
        return self._base_dir / "prompts.json"

    @property
    def settings(self) -> dict[str, Any]:
        return get_json_data(self._settings_json, self._default_settings)

    @property
    def mode(self) -> str:
        return self.settings.get("mode", "cli")

    @property
    def toml_data(self) -> dict[str, Any]:
        try:
            if not self._config_toml.exists():
                logger.warning("TOML file not found: %s", self._config_toml)
                return {}
            with open(self._config_toml, "rb") as f:
                return tomllib.load(f)
        except (tomllib.TOMLDecodeError, OSError) as e:
            logger.warning("Could not read TOML file %s: %s", self._config_toml, e)
            return {}

    @property
    def model(self) -> str:
        return self.settings.get(
            "model", self._default_settings[ConfigKey.MODEL_VERSION]
        )

    @property
    def img_chunk_size(self) -> int:
        return self.settings.get(
            "img_chunk_size", self._default_settings[ConfigKey.IMG_CHUNK_SIZE]
        )

    @property
    def api_delay(self) -> int:
        return self.settings.get(
            "api_delay", self._default_settings[ConfigKey.API_DELAY]
        )

    @property
    def out_of_limit_delay(self) -> int:
        return self.settings.get(
            "out_of_limit_delay", self._default_settings[ConfigKey.OUT_OF_LIMIT_DELAY]
        )

    @property
    def chapter_min_size(self) -> int:
        return self.settings.get(
            "chapter_min_size", self._default_settings[ConfigKey.CHAPTER_MIN_SIZE]
        )

    @property
    def max_api_retries(self) -> int:
        return self.settings.get(
            "max_api_retries", self._default_settings[ConfigKey.MAX_API_RETRIES]
        )

    @property
    def min_chunk_length(self) -> int:
        return self.settings.get(
            "min_chunk_length", self._default_settings[ConfigKey.MIN_CHUNK_LENGTH]
        )

    @property
    def default_prompts(self) -> dict[PromptType, str]:
        return {
            PromptType.IMAGE_PROMPT: (
                "Task: Analyze EACH provided image separately, in the exact order they are given. "
                "Do not skip, merge, or reorder images. "
                "Classify and process each image according to these rules:\n"
                "1. DATA TABLE: Convert its full content strictly into Markdown table format.\n"
                "2. GRAPH (bar, line, pie, etc.): Provide a concise description (up to 100 words) specifying its type, main trend, and key values.\n"
                "3. DIAGRAM/SCHEME (flowchart, architecture, mind map): Provide a description (up to 100 words) explaining what it shows, its main elements, connections, and key conclusion.\n"
                "4. FORMULA/EQUATION: Convert the formula strictly into LaTeX format (e.g., using $...$ or $$...$$).\n"
                "5. DECORATIVE IMAGE (photo, illustration, spacer without data): Return exactly null.\n\n"
                "IMPORTANT: There are exactly {batch_size} images in this request. "
                "Return a JSON array with EXACTLY {batch_size} elements, one per image, "
                "in the same order as the images were provided. Never omit an element — "
                "use null for decorative images instead of skipping them.\n\n"
                "Constraints:\n"
                "- Language: Return all text, descriptions, and tables in the original document's language.\n"
                "- Output Format: Return ONLY a single valid raw JSON array, exactly like this: "
                '["markdown_table_or_description", null, "$E=mc^2$"].\n'
                "- CRITICAL: Do not include any introductory text, explanations, notes, or markdown code block fences (like ```json or ```). Only the raw JSON array."
            ),
            PromptType.PDF_PROMPT: (
                """Task: Extract the structural and textual content from the provided material and represent it in Markdown format for personal analysis and indexing.
                    Guidelines:
                    Process the provided text fragment in detail, maintaining the original structure, headings, and hierarchy.
                    Use ONLY the provided source material. Ensure high fidelity to the original text; if a word is unclear, maintain its visual representation.
                    TABLES: Format all data tables into standard Markdown tables.
                    VISUALS: Provide a concise analytical description of any graphs, diagrams, or schemes, focusing on their main elements and logical connections (up to 100 words per item).
                    LANGUAGE: Keep the output strictly in the original document's language.
                    DATA CLEANING: Fix minor OCR artifacts (e.g., broken words, unnecessary line breaks) to improve readability.
                    OUTPUT: Return the output as raw Markdown content. Focus on accuracy and technical formatting."""
            ),
        }

    def get_prompt_dict(self) -> dict[PromptType, str]:
        raw_data = get_json_data(
            json_file=self.prompts_path,
            default_data={str(k): v for k, v in self.default_prompts.items()},
        )
        return {PromptType(k): v for k, v in raw_data.items()}

    def get_api_key(self) -> str | None:
        if not self._env_path.exists():
            return None
        api_key = self._read_key_from_file()
        if api_key:
            os.environ[self._api_key_name] = api_key
            return api_key
        return None

    def validate_key(self, api_key: str) -> str:
        """
        Verify the key with a real request to Gemini.
        Return api_key:str if is valid or raise ValueError if not.
        Also raises NetworkError, TimeoutError if bad internet connection.
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
            raise NetworkError("Internet connection error. Check your connection.")
        except Exception:
            logger.exception("Unexpected error during API key validation.")
            raise

    def _save_key_to_file(self, api_key: str):
        set_key(self._env_path, self._api_key_name, api_key)

    def _read_key_from_file(self) -> str | None:
        values = dotenv_values(self._env_path)
        return values.get(self._api_key_name)

    def save_and_activate(self, api_key: str):
        self._save_key_to_file(api_key)
        os.environ[self._api_key_name] = api_key

    def _ensure_dir(self, relative_path: str) -> Path:
        path = self._base_dir / relative_path
        path.mkdir(parents=True, exist_ok=True)
        return path
