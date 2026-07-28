import logging
import os
from pathlib import Path

from google import genai
from google.genai.errors import APIError

from config import MODEL_VERSION

logger = logging.getLogger(__name__)


class ConfigManager:
    def __init__(self, base_dir: Path, filename=".env", model: str = MODEL_VERSION):

        self.base_dir = base_dir
        self.env_path = self.base_dir / filename
        self.model = model
        self.api_key_name = "GEMINI_API"

    def get_api_key(self) -> str:
        """Main method: checks the key, prompts for input if necessary, and saves."""
        if self.env_path.exists():
            api_key = self._read_key_from_file()
            if api_key:
                os.environ[self.api_key_name] = api_key
                return api_key

        print("--- First run: configuration settings ---")
        while True:
            user_input = input("Enter your Gemini API key: ").strip()

            if not user_input:
                print("The key cannot be empty. Please try again.")
                continue

            print("Verifying key via Gemini API...")
            if self._validate_key(user_input):
                self._save_key_to_file(user_input)
                os.environ[self.api_key_name] = user_input
                print("Setup completed successfully!\n")
                return user_input
            else:
                print("Invalid key or internet problem. Try again.")

    def _validate_key(self, api_key: str) -> bool:
        """Verify the key with a real request to Gemini."""
        try:
            client = genai.Client(api_key=api_key)
            client.models.generate_content(
                model=self.model,
                contents="Test",
            )
            return True
        except APIError:
            return False
        except (ConnectionError, TimeoutError):
            print("Internet connection error. Check your connection.")
            return False

    def _save_key_to_file(self, api_key: str):
        """Stores the key in an .env file near the .exe."""
        with open(self.env_path, "w", encoding="utf-8") as f:
            f.write(f"{self.api_key_name}={api_key}\n")

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
