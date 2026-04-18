from __future__ import annotations

from .field_base import Field


class Toggle(Field):
    """Boolean toggle rendered as a Flowbite-style switch."""

    _FIELD_TYPE = "toggle"
    _INPUT_TYPE = "checkbox"

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._on_label: str = "On"
        self._off_label: str = "Off"

    def get_on_label(self) -> str:
        return self._on_label

    def get_off_label(self) -> str:
        return self._off_label

    def on_label(self, value: str) -> "Toggle":
        self._on_label = value
        return self

    def off_label(self, value: str) -> "Toggle":
        self._off_label = value
        return self

