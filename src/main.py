import logging

from cli.run_cli import run_cli
from config.config import (
    BASE_DIR,
    DEFAULT_PROMPTS,
    DEFAULT_SETTINGS,
    MODEL_VERSION,
    PROMPTS_JSON_PATH,
)
from config.config_manager import ConfigManager
from config.logging_config import setup_logging
from core.utils import get_json_data
from gui.run_gui import run_gui

logger = logging.getLogger(__name__)


def main():
    settings_json = BASE_DIR / "settings.json"
    settings: dict = get_json_data(
        json_file=settings_json, default_data=DEFAULT_SETTINGS
    )
    mode: str = settings.get("mode", "cli")
    setup_logging(mode=mode)
    config_manager = ConfigManager(
        base_dir=BASE_DIR,
        prompts_path=PROMPTS_JSON_PATH,
        model=MODEL_VERSION,
        default_prompts=DEFAULT_PROMPTS,
    )
    if mode == "cli":
        run_cli(config_manager)
    else:
        run_gui(config_manager)


if __name__ == "__main__":
    main()
