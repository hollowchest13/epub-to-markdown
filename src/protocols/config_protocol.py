# protocols/config_protocol.py
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class ConfigProtocol(Protocol):
    """Contract for Configuration Manager."""

    @property
    def output_dir(self) -> Path: ...

    @property
    def model(self) -> str: ...

    def get_prompt_dict(self) -> dict: ...

    def get_api_key(self) -> str | None: ...
