"""nuru.forms.time — time input."""

from __future__ import annotations

from .base import Field


class Time(Field):
    """Native ``<input type="time">``."""

    _FIELD_TYPE = "text"
    _INPUT_TYPE = "time"
