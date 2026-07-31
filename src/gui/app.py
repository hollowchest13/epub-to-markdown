import threading
import time
from collections.abc import Callable
from tkinter import LEFT

import customtkinter as ctk

from gui.key_dialog import KeyWindow


class App(ctk.CTk):
    def __init__(self, *, processor: Callable, key_changer: Callable):
        super().__init__()
        self.title("Book converter 4 LLM")
        self.geometry("400x250")
        self.progress_frame = ctk.CTkFrame(self)
        self.controls_frame = ctk.CTkFrame(self)
        self._processor = processor
        self._key_changer = key_changer

        self.start_btn = ctk.CTkButton(
            self.controls_frame,
            text="Start",
            command=lambda: self.run_heavy_process(processor=self._processor),
        )
        self.change_key_btn = ctk.CTkButton(
            self.controls_frame,
            text="Change API key",
            command=lambda: self.show_key_window(key_changer=key_changer),
        )
        self.progress = ctk.CTkProgressBar(self.progress_frame)
        self.status_label = ctk.CTkLabel(self.progress_frame, text="Ready")
        self._pack_widgets()

    def show_key_window(self, *, key_changer):
        self.key_window = KeyWindow(key_changer=self._key_changer)

    def _pack_widgets(self):
        PADDING = 10
        self.controls_frame.pack(fill="both", side=LEFT, padx=PADDING, pady=PADDING)
        self.progress_frame.pack(
            expand=True, fill="both", side=LEFT, padx=PADDING, pady=PADDING
        )

        self.start_btn.pack(padx=PADDING, pady=PADDING, side=LEFT)
        self.change_key_btn.pack(padx=PADDING, pady=PADDING, side=LEFT)

    def start_process_thread(self):
        # Блокуємо кнопку, щоб не клікали двічі
        self.start_btn.configure(state="disabled")

        # Запускаємо важку роботу в фоновому потоці
        threading.Thread(target=self.run_heavy_process, daemon=True).start()

    def run_heavy_process(self, processor: Callable):
        # Тут викликається ваша логіка з папки core/
        total_steps = 5
        for i in range(1, total_steps + 1):
            # Імітуємо роботу (парсинг, запит до API тощо)
            time.sleep(1)

            # Рахуємо відсотки (від 0.0 до 1.0)
            progress_value = i / total_steps

            # Оновлюємо UI безпечно через потік
            self.after(
                0,
                self.update_ui,
                progress_value,
                f"Оброблено кроків: {i}/{total_steps}",
            )

        # Коли все готово
        self.after(0, self.finish_process)

    def update_ui(self, value, text):
        self.progress.set(value)
        self.status_label.configure(text=text)

    def finish_process(self):
        self.status_label.configure(text="Конвертацію успішно завершено!")
        self.start_btn.configure(state="normal")


def threaded(func):
    def wrapper(self, *args, **kwargs):
        self.start_btn.configure(state="disabled")
        thread = threading.Thread(target=lambda: run(self, func, *args, **kwargs))
        thread.daemon = True
        thread.start()

    def run(self, func, *args, **kwargs):
        try:
            func(self, *args, **kwargs)
        finally:
            self.start_btn.configure(state="normal")

    return wrapper
