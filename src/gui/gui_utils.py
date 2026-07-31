import threading

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