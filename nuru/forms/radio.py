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


class Radio(Field):
    """Radio button group."""

    _FIELD_TYPE = "radio"
    _INPUT_TYPE = "radio"

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._options: list = []
        self._inline: bool = True

    def get_options(self) -> list:
        return _normalise_options(self._options)

    def is_inline(self) -> bool:
        return self._inline

    def options(self, value: list) -> "Radio":
        self._options = value
        return self

    def inline(self, on: bool = True) -> "Radio":
        self._inline = on
        return self
