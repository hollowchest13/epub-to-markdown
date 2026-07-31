import sys
from pathlib import Path

IMG_CHUNK_SIZE = 15
API_DELAY = 6
OUT_OF_LIMIT_DELAY = 60
CHAPTER_MIN_SIZE = 200
MAX_API_RETRIES = 5
MIN_CHUNK_LENGTH = 50

MODEL_VERSION = "gemini-3.1-flash-lite"

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    print(BASE_DIR)
