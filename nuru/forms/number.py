"""nuru.forms.number — numeric input."""

from __future__ import annotations

from .base import Field


class Number(Field):
    """Numeric ``<input type="number">`` with optional min/max bounds.

    Example::

        Number("age").label("Age").min_value(0).max_value(150)
    """

    _FIELD_TYPE = "text"
    _INPUT_TYPE = "number"

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._min_value: float | None = None
        self._max_value: float | None = None

    # --- Getters ----------------------------------------------------------

    def get_min_value(self) -> float | None:
        return self._min_value

    def get_max_value(self) -> float | None:
        return self._max_value

    # --- Fluent setters ---------------------------------------------------

    def min_value(self, v: float) -> "Number":
        self._min_value = v
        return self

    def max_value(self, v: float) -> "Number":
        self._max_value = v
        return self
