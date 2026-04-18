from __future__ import annotations

from .base import Field


class Radio(Field):
    """Radio button group."""

    _FIELD_TYPE = "radio"
    _INPUT_TYPE = "radio"

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._options: list = []
        self._inline: bool = True

    def get_options(self) -> list:
        return list(self._options)

    def is_inline(self) -> bool:
        return self._inline

    def options(self, value: list) -> "Radio":
        self._options = value
        return self

    def inline(self, on: bool = True) -> "Radio":
        self._inline = on
        return self

