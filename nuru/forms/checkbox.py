"""nuru.forms.checkbox — single boolean checkbox."""

from __future__ import annotations

from .field_base import Field


class Checkbox(Field):
    """Single boolean ``<input type="checkbox">``."""

    _FIELD_TYPE = "checkbox"
    _INPUT_TYPE = "checkbox"
