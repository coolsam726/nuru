"""nuru.forms.email — email address input."""

from __future__ import annotations

from .text import TextInput


class Email(TextInput):
    """Email ``<input type="email">`` with built-in ``email`` validator."""

    _FIELD_TYPE = "text"
    _INPUT_TYPE = "email"

    def __init__(self, key: str) -> None:
        super().__init__(key)
        # ensure the email validator is present by default
        self._validators = ["email"]
