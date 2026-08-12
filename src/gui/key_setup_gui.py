import customtkinter as ctk

from config.config_manager import ConfigManager
from gui.key_dialog import KeyWindow


def setup_key_gui(
    config: ConfigManager, parent: ctk.CTk, window_class: type = KeyWindow
) -> str | None:
    while True:
        window = window_class(parent)
        parent.wait_window(window)

        if not window.api_key:
            return None
        if config.save_and_activate(window.api_key):
            return window.api_key
