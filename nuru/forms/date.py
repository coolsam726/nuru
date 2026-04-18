"""nuru.forms.date — date input."""

from __future__ import annotations

from .field_base import Field


class Date(Field):
    """Native ``<input type="date">``."""

    _FIELD_TYPE = "text"
    _INPUT_TYPE = "date"
