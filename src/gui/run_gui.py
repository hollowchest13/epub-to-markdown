import logging
from pathlib import Path

from google import genai

from config.config import BASE_DIR
from config.config_manager import ConfigManager
from controllers.app_controller import AppController
from gui.app import App

logger = logging.getLogger(__name__)


def run_gui(config_manager: ConfigManager):
    client = genai.Client(api_key=config_manager.get_api_key())
    app_controller = AppController(api_client=client)
    app = App(app_controller)
    app.mainloop()
