from cli.run_cli import run_cli
from gui.run_gui import run_gui
from pathlib import Path
import logging
from config.config import BASE_DIR
from config.logging_config import setup_console_logging,setup_file_logging
from config.config_manager import get_settings,ConfigManager
logger = logging.getLogger(__name__)

def main():
    settings_json=BASE_DIR/"settings.json"
    settings:dict=get_settings(settings_json=settings_json)
    mode:str=settings.get("mode","gui")
    config_manager = ConfigManager(base_dir=BASE_DIR)
    if mode=="cli":
        setup_console_logging()
        run_cli(config_manager)

    else:
        log_path:Path=BASE_DIR/"app.log"
        log_path.parent.mkdir(exist_ok=True)
        setup_file_logging(log_path=log_path)
        run_gui(config_manager)


if __name__ == "__main__":
    main()
