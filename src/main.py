import logging

from cli.run_cli import run_cli
from config.config import BASE_DIR
from config.config_manager import ConfigManager, get_settings
from config.logging_config import setup_logging
from gui.run_gui import run_gui

logger = logging.getLogger(__name__)


def main():
    settings_json = BASE_DIR / "settings.json"
    settings: dict = get_settings(settings_json=settings_json)
    mode: str = settings.get("mode", "gui")
    setup_logging(mode=mode)
    config_manager = ConfigManager(base_dir=BASE_DIR)
    if mode == "cli":
        run_cli(config_manager)
    else:
        run_gui(config_manager)


if __name__ == "__main__":
    main()
