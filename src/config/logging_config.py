import logging
from logging.handlers import RotatingFileHandler

from config.config import BASE_DIR


def setup_logging(mode: str, level: int = logging.INFO):
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    if mode == "cli":
        handler = logging.StreamHandler()
    else:
        log_path = BASE_DIR / "app.log"
        log_path.parent.mkdir(exist_ok=True)
        handler = RotatingFileHandler(
            log_path, maxBytes=5 * 1024 * 1024, backupCount=1, encoding="utf-8"
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    root_logger.addHandler(handler)
