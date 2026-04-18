"""nuru.infolists.base — Infolist container class."""
from __future__ import annotations
from typing import Any
class Infolist:
    """
    Reusable infolist owning display entries shown on the view/detail page.
    Entries are SEPARATE from form fields.
    If a resource defines no Infolist, the ViewPage auto-derives entries from the Form.
    """
    def __init__(self) -> None:
        self._entries: list[Any] = []
        self._cols: int = 2
        self._title: str = ""
    @classmethod
    def make(cls, entries: list[Any] | None = None) -> "Infolist":
        obj = cls()
        if entries is not None:
            obj._entries = list(entries)
        return obj
    def entries(self) -> list[Any]:
        return list(self._entries)
    def schema(self, entries: list[Any]) -> "Infolist":
        self._entries = list(entries); return self
    def add_entry(self, entry: Any) -> "Infolist":
        self._entries.append(entry); return self
    def cols(self, value: int) -> "Infolist":
        self._cols = value; return self
    def title(self, value: str) -> "Infolist":
        self._title = value; return self
    def get_cols(self) -> int: return self._cols
    def get_title(self) -> str: return self._title
    def __repr__(self) -> str:
        return f"{type(self).__name__}(entries={len(self.entries())})"
