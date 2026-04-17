"""nuru.forms.email — email address input."""

from __future__ import annotations

from .base import Field


class Email(Field):
    """Email ``<input type="email">`` with built-in ``email`` validator."""

    _FIELD_TYPE = "text"
    _INPUT_TYPE = "email"

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._validators = ["email"]
