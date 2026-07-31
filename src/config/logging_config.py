import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_console_logging():
    logging.basicConfig(level=logging.INFO)

def setup_file_logging(log_path: Path, max_bytes: int = 5 * 1024 * 1024, backup_count: int = 1):
    handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])