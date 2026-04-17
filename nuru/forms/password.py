"""nuru.forms.password — password input."""

from __future__ import annotations

from .text import TextInput


class Password(TextInput):
    """Password ``<input type="password">``."""

    _FIELD_TYPE = "password"
    _INPUT_TYPE = "password"
