import threading
import time

import customtkinter as ctk


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Book converter 4 LLM")
        self.geometry("400x250")
        self.api_key_entry = ctk.CTkEntry(
            self,
        )
        self.api_key_entry.pack()
        self.progress_frame = ctk.CTkFrame(self)
        self.controls_frame = ctk.CTkFrame(self)

        self.start_btn = ctk.CTkButton(
            self.controls_frame, text="Start", command=self.start_process_thread
        )
        self.set_key_btn = ctk.CTkButton(
            self.controls_frame, text="Set API key", command=self._set_key
        )
        self.progress = ctk.CTkProgressBar(self.progress_frame)
        self.status_label = ctk.CTkLabel(self, text="Ready")

    def _set_key(self):
        pass

    def _pack_widgets(self):
        PADDING = 10
        self.progress_frame.pack(padx=PADDING, pady=PADDING, fill="x")

    def start_process_thread(self):
        # Блокуємо кнопку, щоб не клікали двічі
        self.start_btn.configure(state="disabled")

        # Запускаємо важку роботу в фоновому потоці
        threading.Thread(target=self.run_heavy_process, daemon=True).start()

    def run_heavy_process(self):
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


if __name__ == "__main__":
    app = App()
    app.mainloop()
