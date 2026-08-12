import logging

from config.config_manager import ConfigManager
from controllers.app_controller import AppController
from controllers.key_win_controller import KeyWinController
from gui.app import App

logger = logging.getLogger(__name__)


def run_gui(config_manager: ConfigManager):
    app_controller = AppController(config_manager=config_manager)
    key_win_controller = KeyWinController(config_manager=config_manager)
    app = App(app_controller=app_controller, key_win_controller=key_win_controller)
    app.mainloop()
