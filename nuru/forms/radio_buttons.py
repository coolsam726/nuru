from __future__ import annotations

from .field_base import Field


class RadioButtons(Field):
    """Group of radio buttons rendered as pill-like choices."""

    _FIELD_TYPE = "radio_buttons"
    _INPUT_TYPE = "radio"

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._options: list = []

    def get_options(self) -> list:
        return list(self._options)

    def options(self, value: list) -> "RadioButtons":
        self._options = value
        return self

