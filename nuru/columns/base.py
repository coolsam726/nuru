"""nuru.columns.base — Column base class with fluent API."""
from __future__ import annotations
from typing import Any


class Column:
    """Base column. Subclass to add rendering logic."""

    _COLUMN_TYPE: str = "text"

    def __init__(self, key: str, label: str = "", sortable: bool = False) -> None:
        self._key = key
        self._label = label or key.replace("_", " ").title()
        self._sortable = sortable

    # ------------------------------------------------------------------ #
    # Factory                                                              #
    # ------------------------------------------------------------------ #
    @classmethod
    def make(cls, key: str) -> "Column":
        return cls(key)

    # ------------------------------------------------------------------ #
    # Fluent setters                                                       #
    # ------------------------------------------------------------------ #
    def label(self, value: str) -> "Column":
        self._label = value; return self

    def sortable(self, on: bool = True) -> "Column":
        self._sortable = on; return self

    # ------------------------------------------------------------------ #
    # Getters                                                              #
    # ------------------------------------------------------------------ #
    def get_key(self) -> str: return self._key
    def get_label(self) -> str: return self._label
    def is_sortable(self) -> bool: return self._sortable
    def get_column_type(self) -> str: return self._COLUMN_TYPE

    # Alias for template compatibility
    @property
    def key(self) -> str: return self._key

    # ------------------------------------------------------------------ #
    # Rendering                                                            #
    # ------------------------------------------------------------------ #
    def render(self, value: Any) -> str:
        if value is None or value == "":
            return "—"
        return str(value)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(key={self._key!r}, label={self._label!r})"

