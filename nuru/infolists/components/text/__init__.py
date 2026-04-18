from ..base import Entry
class TextEntry(Entry):
    _ENTRY_TYPE = "text"
    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._max_length: int | None = None
    def max_length(self, n: int) -> "TextEntry":
        self._max_length = n; return self
    def get_max_length(self): return self._max_length
    def render(self, value):
        v = super().render(value)
        if self._max_length and v != self._placeholder and len(v) > self._max_length:
            return v[:self._max_length] + "…"
        return v
