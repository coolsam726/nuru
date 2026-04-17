"""nuru.forms.hidden — hidden input field."""

from __future__ import annotations

from .base import Field


class Hidden(Field):
    """``<input type="hidden">`` — never shown to the user."""

    _FIELD_TYPE = "hidden"
    _INPUT_TYPE = "hidden"
