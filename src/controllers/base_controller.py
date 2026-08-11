from collections.abc import Callable


class BaseController:
    def __init__(self):
        self._event_handlers: dict[str, Callable] = {}

    def on(self, event: str, callback: Callable):
        self._event_handlers[event] = callback

    def _emit(self, event: str, **kwargs):
        if handler := self._event_handlers.get(event):
            handler(**kwargs)
