from collections.abc import Callable
from tkinter import LEFT, filedialog

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox

from config.config import BASE_DIR
from controllers.app_controller import AppController
from controllers.key_win_controller import KeyWinController
from gui.key_dialog import KeyWindow


class App(ctk.CTk):
    def __init__(
        self, app_controller: AppController, key_win_controller: KeyWinController
    ):
        super().__init__()
        self.title("Book converter 4 LLM")
        self.geometry("600x100")
        self.progress_frame = ctk.CTkFrame(self)
        self.controls_frame = ctk.CTkFrame(self)
        self._controller = app_controller
        self._controller.on(event="no_api_key", callback=self.show_key_window)

        self._controller.gui_callback = self.update_progress_ui
        self._key_win_controller = key_win_controller
        self._key_win_controller.on(event="show_msg", callback=self.show_msg)

        self.start_btn = ctk.CTkButton(
            self.controls_frame,
            text="Start",
            command=self._on_start,
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

    def show_msg(self, *, msg: str, msg_type: str):
        title = {
            "error": "Error",
            "success": "Success",
            "info": "Info",
        }.get(msg_type, "Info")

        icon_map = {"error": "cancel", "success": "check", "info": "info"}
        icon = icon_map.get(msg_type, "info")

        def _show():
            master = (
                self.key_window
                if hasattr(self, "key_window") and self.key_window.winfo_exists()
                else self
            )
            CTkMessagebox(
                master=master, title=title, message=msg, icon=icon, option_1="OK"
            )

        self.after(200, _show)

    def _set_ui_locked(self, locked: bool):
        state = "disabled" if locked else "normal"
        self.start_btn.configure(state=state)
        self.change_key_btn.configure(state=state)
        if locked:
            self.progress.configure(mode="indeterminate")
            self.progress.start()
            self.progress_label.configure(text="Processing...")
        else:
            self.progress.stop()
            self.progress.configure(mode="determinate")
            self.progress.set(1)
            self.progress_label.configure(text="Done")

    def _on_start(self):
        api_key = self._controller.get_api_key()
        if not api_key:
            api_key = self.show_key_window(on_save=self._on_start)
            return

        files = filedialog.askopenfilenames(
            title="Select files",
            initialdir=BASE_DIR,
            filetypes=[
                ("Documents", "*.pdf *.epub *.md"),
                ("PDF files", "*.pdf"),
                ("EPUB files", "*.epub"),
                ("Markdown files", "*.md"),
            ],
        )
        if not files:
            return
        self._set_ui_locked(True)
        self._controller.convert_files(
            files=files,
            api_key=api_key,
            on_done=lambda: self.after(0, self._set_ui_locked, False),
        )

    def show_key_window(self, on_save: Callable | None = None):
        if hasattr(self, "key_window") and self.key_window.winfo_exists():
            self.key_window.focus()
            return
        self.key_window = KeyWindow(self, controller=self._key_win_controller)
        self.key_window.grab_set()

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

        if len(text) > 60:
            text = f"{text[:30]}...{text[-30:]}"

        self.after(0, lambda: self._apply_ui_update(value, text))

    def _apply_ui_update(self, progress_value: float, text: str):
        if self.progress.cget("mode") == "indeterminate":
            self.progress.stop()
            self.progress.configure(mode="determinate")
        self.progress.set(progress_value)
        self.progress_label.configure(text=text)
