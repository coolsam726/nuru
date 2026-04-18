from ..base import Entry
from typing import Any
class BooleanEntry(Entry):
    _ENTRY_TYPE = "boolean"
    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._true_label = "Yes"; self._false_label = "No"
    def labels(self, true_label: str, false_label: str) -> "BooleanEntry":
        self._true_label = true_label; self._false_label = false_label; return self
    def get_true_label(self): return self._true_label
    def get_false_label(self): return self._false_label
    def render(self, value: Any) -> str:
        return self._true_label if value else self._false_label
