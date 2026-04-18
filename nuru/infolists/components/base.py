"""nuru.infolists.components.base — Entry base class."""
from __future__ import annotations
from typing import Any
class Entry:
    """Base class for all infolist display entries."""
    _ENTRY_TYPE: str = "text"
    def __init__(self, key: str) -> None:
        self._key = key
        self._label: str = key.replace("_", " ").title()
        self._col_span: int | str = 1
        self._css_class: str = ""
        self._visible: bool = True
        self._placeholder: str = "—"
        self._url_prefix: str = ""
    @classmethod
    def make(cls, key: str) -> "Entry":
        return cls(key)
    def get_key(self) -> str: return self._key
    def get_label(self) -> str: return self._label
    def get_entry_type(self) -> str: return self._ENTRY_TYPE
    def get_col_span(self) -> int | str: return self._col_span
    def get_css_class(self) -> str: return self._css_class
    def is_visible(self) -> bool: return self._visible
    def get_placeholder(self) -> str: return self._placeholder
    def get_url_prefix(self) -> str: return self._url_prefix
    def label(self, value: str) -> "Entry":
        self._label = value; return self
    def col_span(self, value: int | str) -> "Entry":
        self._col_span = value; return self
    def css_class(self, value: str) -> "Entry":
        self._css_class = value; return self
    def visible(self, on: bool = True) -> "Entry":
        self._visible = on; return self
    def placeholder(self, value: str) -> "Entry":
        self._placeholder = value; return self
    def url_prefix(self, value: str) -> "Entry":
        self._url_prefix = value; return self
    @property
    def template_name(self) -> str:
        return f"infolist_{self._ENTRY_TYPE}.html"

    # ------------------------------------------------------------------ #
    # Compatibility with the legacy detail_item macro                     #
    # These let Entry objects pass through the same rendering path as     #
    # legacy Field objects without any template changes.                  #
    # ------------------------------------------------------------------ #

    def get_field_type(self) -> str:
        """Alias for get_entry_type() — used by detail_item macro."""
        return self._ENTRY_TYPE

    def is_section_field(self) -> bool:
        """Entries are never section containers."""
        return False
    def render(self, value: Any) -> str:
        if value is None or str(value).strip() == "":
            return self._placeholder
        return str(value)
    def __repr__(self) -> str:
        return f"{type(self).__name__}(key={self._key!r})"
