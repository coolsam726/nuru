"""nuru.columns.image — image thumbnail column."""
from __future__ import annotations
from typing import Any
from .base import Column


class Image(Column):
    """Renders a stored file path as an ``<img>`` thumbnail."""

    _COLUMN_TYPE = "image"

    _DEFAULT_PLACEHOLDER = (
        "M16 7a4 4 0 11-8 0 4 4 0 018 0z"
        "M12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
    )

    def __init__(self, key: str, label: str = "", sortable: bool = False,
                 url_prefix: str = "",
                 img_class: str = "w-8 h-8 rounded-full object-cover",
                 placeholder_icon: str | None = None) -> None:
        super().__init__(key, label, sortable)
        self._url_prefix = url_prefix
        self._img_class = img_class
        self._placeholder_icon = placeholder_icon or self._DEFAULT_PLACEHOLDER

    def url_prefix(self, value: str) -> "Image":
        self._url_prefix = value; return self

    def img_class(self, value: str) -> "Image":
        self._img_class = value; return self

    def placeholder_icon(self, value: str) -> "Image":
        self._placeholder_icon = value; return self

    def get_url_prefix(self) -> str: return self._url_prefix
    def get_img_class(self) -> str: return self._img_class
    def get_placeholder_icon(self) -> str: return self._placeholder_icon

    def get_url(self, value: Any) -> str | None:
        if not value or str(value).strip() == "":
            return None
        v = str(value).strip()
        if v.startswith(("http://", "https://", "/")):
            return v
        prefix = self._url_prefix.rstrip("/")
        return f"{prefix}/{v}"

    def render(self, value: Any) -> str:
        url = self.get_url(value)
        return url or ""

