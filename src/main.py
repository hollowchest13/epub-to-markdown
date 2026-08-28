import logging

from cli.run_cli import run_cli
from config.config import (
    BASE_DIR,
    MODEL_VERSION,
)
from config.config_manager import ConfigManager
from config.logging_config import setup_logging
from gui.run_gui import run_gui
from server.run_api import run_api

logger = logging.getLogger(__name__)


def main():
    config_manager = ConfigManager(
        base_dir=BASE_DIR,
        model=MODEL_VERSION,
    )
    mode = config_manager.mode
    setup_logging(mode=config_manager.mode)
    match mode:
        case "cli":
            run_cli(config_manager)
        case "gui":
            run_gui(config_manager)
        case "api":
            run_api(config_manager)


if __name__ == "__main__":
    main()
