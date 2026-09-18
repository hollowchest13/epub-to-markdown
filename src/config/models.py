from enum import StrEnum, auto


class ConfigKey(StrEnum):
    MODE = auto()
    IMG_CHUNK_SIZE = auto()
    API_DELAY = auto()
    OUT_OF_LIMIT_DELAY = auto()
    CHAPTER_MIN_SIZE = auto()
    MAX_API_RETRIES = auto()
    MIN_CHUNK_LENGTH = auto()
    MODEL_VERSION = auto()
