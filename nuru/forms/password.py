"""nuru.forms.password — password input."""

from __future__ import annotations

from .base import Field


class Password(Field):
    """Password ``<input type="password">``."""

    _FIELD_TYPE = "password"
    _INPUT_TYPE = "password"
