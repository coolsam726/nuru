from ..base import Entry
from typing import Any
_COLORS = {
    "green":"bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
    "red":"bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
    "amber":"bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
    "blue":"bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300",
    "gray":"bg-secondary-100 text-secondary-700 dark:bg-secondary-700 dark:text-secondary-300",
}
class BadgeEntry(Entry):
    _ENTRY_TYPE = "badge"
    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._colors: dict[str, str] = {}
    def colors(self, mapping: dict) -> "BadgeEntry":
        self._colors = mapping; return self
    def get_css(self, value: Any) -> str:
        color = self._colors.get(str(value), "gray")
        return _COLORS.get(color, _COLORS["gray"])
