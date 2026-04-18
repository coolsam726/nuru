"""nuru.columns.text — plain text column."""
from __future__ import annotations
from typing import Any
from .base import Column


class Text(Column):
    """Renders a value as plain text, with optional truncation."""

    _COLUMN_TYPE = "text"

    def __init__(self, key: str, label: str = "", sortable: bool = False,
                 max_length: int | None = None) -> None:
        super().__init__(key, label, sortable)
        self._max_length = max_length

    def max_length(self, value: int) -> "Text":
        self._max_length = value; return self

    def get_max_length(self) -> int | None: return self._max_length

    def render(self, value: Any) -> str:
        if value is None or value == "":
            return "—"
        s = str(value)
        if self._max_length and len(s) > self._max_length:
            return s[:self._max_length] + "…"
        return s

