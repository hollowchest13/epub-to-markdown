from tkinter import LEFT

import customtkinter as ctk

from controllers.app_controller import AppController
from controllers.key_win_controller import KeyWinController
from gui.key_dialog import KeyWindow


class App(ctk.CTk):
    def __init__(self, app_controller: AppController):
        super().__init__()
        self.title("Book converter 4 LLM")
        self.geometry("600x100")
        self.progress_frame = ctk.CTkFrame(self)
        self.controls_frame = ctk.CTkFrame(self)
        self._controller = app_controller
        self._controller.gui_callback = self.update_progress_ui

        self.start_btn = ctk.CTkButton(
            self.controls_frame,
            text="Start",
            command=self._controller.handle_start,
        )
        self.change_key_btn = ctk.CTkButton(
            self.controls_frame,
            text="Change API key",
            command=self.show_key_window,
        )
        self.progress = ctk.CTkProgressBar(self.progress_frame)
        self.progress.set(0)
        self.progress_label = ctk.CTkLabel(self.progress_frame, text="Ready")
        self.status_text = ctk.CTkTextbox(self.progress_frame)
        self._pack_widgets()

    def show_key_window(self):
        if hasattr(self, "key_window") and self.key_window.winfo_exists():
            self.key_window.focus()
            return
        key_win_controller = KeyWinController()
        self.key_window = KeyWindow(self, controller=key_win_controller)

    def _pack_widgets(self):
        PADDING = 5
        self.progress_frame.pack(
            side=LEFT, fill="both", expand=True, padx=PADDING, pady=PADDING
        )
        self.controls_frame.pack(
            side=LEFT, fill="y", expand=False, padx=PADDING, pady=PADDING
        )
        self.progress_frame.grid_rowconfigure(0, weight=1)
        self.progress_frame.grid_rowconfigure(1, weight=0)
        self.progress_frame.grid_rowconfigure(2, weight=0)
        self.progress_frame.grid_rowconfigure(3, weight=1)
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_label.grid(
            row=1, column=0, sticky="ew", padx=PADDING, pady=(0, 2)
        )
        self.progress.grid(row=2, column=0, sticky="ew", padx=PADDING, pady=(2, 0))
        self.controls_frame.grid_rowconfigure(0, weight=1)
        self.controls_frame.grid_rowconfigure(1, weight=0)
        self.controls_frame.grid_rowconfigure(2, weight=0)
        self.controls_frame.grid_rowconfigure(3, weight=1)
        self.controls_frame.grid_columnconfigure(0, weight=1)
        self.start_btn.grid(row=1, column=0, sticky="ew", padx=PADDING, pady=(0, 3))
        self.change_key_btn.grid(
            row=2, column=0, sticky="ew", padx=PADDING, pady=(3, 0)
        )

    def update_progress_ui(self, *, current: int, total: int, text: str = ""):

        value = current / total if total > 0 else 0.0
        self.after(0, lambda: self._apply_ui_update(value, text))

    def _apply_ui_update(self, progress_value: float, text: str):

        self.progress.set(progress_value)
        self.progress_label.configure(text=text)
