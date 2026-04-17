"""nuru.forms.textarea — multi-line text area."""

from __future__ import annotations

from .base import Field


class Textarea(Field):
    """Multi-line ``<textarea>`` input.

    Example::

        Textarea("bio").label("Biography").rows(6).placeholder("Tell us about yourself…")
    """

    _FIELD_TYPE = "textarea"
    _INPUT_TYPE = "textarea"

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._rows: int = 4

    # --- Getters ----------------------------------------------------------

    def get_rows(self) -> int:
        return self._rows

    # --- Fluent setters ---------------------------------------------------

    def rows(self, n: int) -> "Textarea":
        self._rows = n
        return self
