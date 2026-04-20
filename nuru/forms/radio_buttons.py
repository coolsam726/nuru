from __future__ import annotations

from .field_base import Field


def _normalise_options(opts: list) -> list[dict]:
    out = []
    for item in opts:
        if isinstance(item, dict):
            out.append(item)
        elif isinstance(item, (tuple, list)) and len(item) == 2:
            out.append({"value": item[0], "label": item[1]})
        else:
            out.append({"value": item, "label": item})
    return out


class RadioButtons(Field):
    """Group of radio buttons rendered as pill-like choices."""

    _FIELD_TYPE = "radio_buttons"
    _INPUT_TYPE = "radio"

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._options: list = []

    def get_options(self) -> list:
        return _normalise_options(self._options)

    def options(self, value: list) -> "RadioButtons":
        self._options = value
        return self

