# protocols/config_protocol.py
from pathlib import Path
from typing import Protocol, runtime_checkable

from core.models import PromptType


@runtime_checkable
class ConfigProtocol(Protocol):
    """Contract for Configuration Manager."""

    @property
    def output_dir(self) -> Path: ...

    @property
    def model(self) -> str: ...

    def get_prompt_dict(self) -> dict[PromptType, str]: ...

    def get_api_key(self) -> str | None: ...
