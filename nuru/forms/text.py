"""nuru.forms.text — single-line text input."""

from __future__ import annotations

from .base import Field


class TextInput(Field):
    """Single-line text input base class.

    This is the modern base class for single-line inputs.  For backwards
    compatibility the old ``Text`` name is preserved as a thin subclass of
    :class:`TextInput`.

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

    def max_length(self, n: int) -> "TextInput":
        self._max_length = n
        return self


class Text(TextInput):
    """Backward-compatible alias for :class:`TextInput`.

    Existing code that imports ``Text`` continues to work.
    """
    pass

