"""nuru.columns.boolean — boolean column."""
from __future__ import annotations
from typing import Any
from .base import Column


class Boolean(Column):
    """Renders a boolean value as a labeled badge."""

    _COLUMN_TYPE = "boolean"

    def __init__(self, key: str, label: str = "", sortable: bool = False,
                 true_label: str = "Yes", false_label: str = "No") -> None:
        super().__init__(key, label, sortable)
        self._true_label = true_label
        self._false_label = false_label

    def labels(self, true_label: str, false_label: str) -> "Boolean":
        self._true_label = true_label
        self._false_label = false_label
        return self

    def get_true_label(self) -> str: return self._true_label
    def get_false_label(self) -> str: return self._false_label

    def render(self, value: Any) -> str:
        return self._true_label if value else self._false_label

    def is_true(self, value: Any) -> bool:
        return bool(value)

