from ..base import Entry
from typing import Any
class FileEntry(Entry):
    _ENTRY_TYPE = "file"
    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._download_label = "Download"
    def download_label(self, value: str) -> "FileEntry":
        self._download_label = value; return self
    def get_download_label(self): return self._download_label
    def get_url(self, value: Any) -> str | None:
        if not value or str(value).strip() == "": return None
        v = str(value).strip()
        if v.startswith(("http://","https://","/")): return v
        prefix = self._url_prefix.rstrip("/")
        return f"{prefix}/{v}" if prefix else v
