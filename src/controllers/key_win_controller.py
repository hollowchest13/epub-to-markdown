import logging

from config.config_manager import ConfigManager
from controllers.base_controller import BaseController

logger = logging.getLogger(__name__)


class KeyWinController(BaseController):
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self._config_manager = config_manager

    def save_key(self, api_key: str):
        try:
            api_key = self._config_manager.validate_key(api_key)
            self._config_manager.save_and_activate(api_key=api_key)
            self._emit("close_window")
        except ValueError:
            self._emit("show_msg", msg="Invalid API key.", msg_type="error")
        except (ConnectionError, TimeoutError):
            self._emit(
                "show_msg",
                msg="Connection error. Check your internet.",
                msg_type="error",
            )
        except Exception:
            logger.exception("Unexpected error during key save.")
            self._emit("show_msg", msg="Unexpected error.", msg_type="error")
