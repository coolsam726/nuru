from ..base import Entry
from typing import Any
class DateEntry(Entry):
    _ENTRY_TYPE = "date"
    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._fmt = "%d %b %Y"
        self._date_only = True
    def format(self, fmt: str) -> "DateEntry":
        self._fmt = fmt; return self
    def datetime(self) -> "DateEntry":
        self._date_only = False; self._fmt = "%d %b %Y, %H:%M"; return self
    def render(self, value: Any) -> str:
        if not value: return self._placeholder
        from datetime import datetime, date
        if isinstance(value, (datetime, date)):
            return value.strftime(self._fmt)
        try:
            return datetime.fromisoformat(str(value)).strftime(self._fmt)
        except Exception:
            return str(value)
