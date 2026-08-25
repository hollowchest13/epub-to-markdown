from collections.abc import Callable

import customtkinter as ctk


class KeyWindow(ctk.CTkToplevel):
    def __init__(
        self, master, *, controller, on_save: Callable = lambda *args, **kwargs: None
    ):
        super().__init__(master)
        self.title("Enter gemini API key")
        self.geometry("350x180")
        self.resizable(False, False)
        self.api_key = None
        self._controller = controller

        self.label = ctk.CTkLabel(
            self, text="An API key is required for the program to work:"
        )
        self.label.pack(pady=(20, 10))

        self.entry = ctk.CTkEntry(
            self, width=280, placeholder_text="Insert the key here...", show="*"
        )
        self.entry.pack(pady=5)

        self.btn = ctk.CTkButton(self, text="Save and continue", command=self._on_save)
        self.btn.pack(pady=15)
        self._on_save_callback = on_save

    def _on_save(self):
        self._controller.save_key(api_key=self.entry.get().strip())
        self.grab_release()
        self.destroy()
        self._on_save_callback()
