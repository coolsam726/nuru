"""nuru.forms.text — single-line text input."""

from __future__ import annotations

from .base import Field


class Text(Field):
    """Single-line text ``<input>``.

    Example::

        Text("username").label("Username").required().placeholder("johndoe")
    """

    _FIELD_TYPE = "text"
    _INPUT_TYPE = "text"

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._max_length: int | None = None

    # --- Getters ----------------------------------------------------------

    def get_max_length(self) -> int | None:
        return self._max_length

    # --- Fluent setters ---------------------------------------------------

    def max_length(self, n: int) -> "Text":
        self._max_length = n
        return self
