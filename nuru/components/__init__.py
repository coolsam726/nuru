"""nuru.components — additional field types backed by Flowbite widgets."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from nuru.forms.base import Field

if TYPE_CHECKING:
    from nuru.panel import AdminPanel


def register_components(panel: "AdminPanel") -> None:
    """Register component templates with *panel*. Call once during app setup."""
    panel.add_template_dir(Path(__file__).parent / "templates")


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


class Timepicker(Field):
    """Time input backed by the Flowbite timepicker widget."""

    _FIELD_TYPE = "timepicker"
    _INPUT_TYPE = "text"

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._time_format: str = "HH:MM"
        self._placeholder = "HH:MM"

    def get_time_format(self) -> str:
        return self._time_format

    def time_format(self, fmt: str) -> "Timepicker":
        self._time_format = fmt
        return self
