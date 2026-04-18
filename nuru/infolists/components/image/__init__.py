from ..base import Entry
from typing import Any
class ImageEntry(Entry):
    _ENTRY_TYPE = "image"
    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._img_class: str = "w-16 h-16 object-cover rounded"
        self._placeholder_icon: str = "M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
    def avatar(self) -> "ImageEntry":
        self._img_class = "w-24 h-24 rounded-full object-cover"
        self._placeholder_icon = "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
        return self
    def img_class(self, value: str) -> "ImageEntry":
        self._img_class = value; return self
    def placeholder_icon(self, value: str) -> "ImageEntry":
        self._placeholder_icon = value; return self
    def get_img_class(self) -> str: return self._img_class
    def get_placeholder_icon(self) -> str: return self._placeholder_icon
    def get_url(self, value: Any) -> str | None:
        if not value or str(value).strip() == "":
            return None
        v = str(value).strip()
        if v.startswith(("http://","https://","/")):
            return v
        prefix = self._url_prefix.rstrip("/")
        return f"{prefix}/{v}" if prefix else v
