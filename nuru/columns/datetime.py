"""nuru.columns.datetime — date/datetime column."""
from __future__ import annotations
from typing import Any
from .base import Column


class DateTime(Column):
    """Renders a date or datetime value using a strftime format."""

    _COLUMN_TYPE = "datetime"

    def __init__(self, key: str, label: str = "", sortable: bool = False,
                 fmt: str = "%d %b %Y, %H:%M", date_only: bool = False) -> None:
        super().__init__(key, label, sortable)
        self._fmt = fmt
        self._date_only = date_only

    def format(self, value: str) -> "DateTime":
        self._fmt = value; return self

    def date_only(self, on: bool = True) -> "DateTime":
        self._date_only = on; return self

    def get_format(self) -> str: return self._fmt
    def is_date_only(self) -> bool: return self._date_only

    def render(self, value: Any) -> str:
        if value is None or value == "":
            return "—"
        from datetime import datetime, date
        fmt = "%d %b %Y" if self._date_only else self._fmt
        if isinstance(value, (datetime, date)):
            return value.strftime(fmt)
        try:
            return datetime.fromisoformat(str(value)).strftime(fmt)
        except (ValueError, TypeError):
            return str(value)

