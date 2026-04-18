"""nuru.tables.base — Table container class."""
from __future__ import annotations
from typing import Any
class Table:
    """Reusable table container owning columns and row actions."""
    def __init__(self) -> None:
        self._columns: list[Any] = []
        self._row_actions: list[Any] = []
        self._per_page: int = 20
        self._searchable: bool = True
        self._default_sort: str = ""
        self._default_sort_dir: str = "asc"
    @classmethod
    def make(cls, columns: list[Any] | None = None) -> "Table":
        obj = cls()
        if columns is not None:
            obj._columns = list(columns)
        return obj
    def columns(self) -> list[Any]:
        return list(self._columns)
    def row_actions(self) -> list[Any]:
        return list(self._row_actions)
    def schema(self, columns: list[Any]) -> "Table":
        self._columns = list(columns); return self
    def add_column(self, col: Any) -> "Table":
        self._columns.append(col); return self
    def set_row_actions(self, actions: list[Any]) -> "Table":
        self._row_actions = list(actions); return self
    def add_row_action(self, action: Any) -> "Table":
        self._row_actions.append(action); return self
    def per_page(self, value: int) -> "Table":
        self._per_page = value; return self
    def searchable(self, on: bool = True) -> "Table":
        self._searchable = on; return self
    def default_sort(self, key: str, direction: str = "asc") -> "Table":
        self._default_sort = key; self._default_sort_dir = direction; return self
    def get_per_page(self) -> int: return self._per_page
    def is_searchable(self) -> bool: return self._searchable
    def get_default_sort(self) -> str: return self._default_sort
    def get_default_sort_dir(self) -> str: return self._default_sort_dir
    def __repr__(self) -> str:
        return f"{type(self).__name__}(columns={len(self.columns())})"
