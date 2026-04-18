"""nuru.columns.badge — colored badge column."""
from __future__ import annotations
from typing import Any
from .base import Column


class Badge(Column):
    """Renders a value as a colored badge pill."""

    _COLUMN_TYPE = "badge"

    _COLOR_CLASSES = {
        "green":  "bg-green-100 text-green-800",
        "red":    "bg-red-100 text-red-800",
        "amber":  "bg-amber-100 text-amber-800",
        "blue":   "bg-blue-100 text-blue-800",
        "purple": "bg-purple-100 text-purple-800",
        "pink":   "bg-pink-100 text-pink-800",
        "gray":   "bg-slate-100 text-slate-700",
    }

    def __init__(self, key: str, label: str = "", sortable: bool = False,
                 colors: dict[str, str] | None = None) -> None:
        super().__init__(key, label, sortable)
        self._colors: dict[str, str] = colors or {}

    def colors(self, mapping: dict[str, str]) -> "Badge":
        self._colors = mapping; return self

    def get_colors(self) -> dict[str, str]: return self._colors

    def css_classes(self, value: Any) -> str:
        color = self._colors.get(str(value), "gray")
        return self._COLOR_CLASSES.get(color, self._COLOR_CLASSES["gray"])

    def render(self, value: Any) -> str:
        if value is None or value == "":
            return "—"
        return str(value)

