"""nuru.forms.timepicker — Flowbite-styled time input field."""

from __future__ import annotations

from .field_base import Field


class TimePicker(Field):
    """Time picker field using a Flowbite-styled native time input.

    Example::

        TimePicker("opens_at").label("Opening time")
        TimePicker("slot").label("Time slot").min_time("08:00").max_time("18:00")
    """

    _FIELD_TYPE = "timepicker"
    _INPUT_TYPE = "time"

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._min_time: str = ""
        self._max_time: str = ""
        self._step: int = 0  # 0 = browser default; seconds otherwise

    # --- Getters ----------------------------------------------------------

    def get_min_time(self) -> str:
        return self._min_time

    def get_max_time(self) -> str:
        return self._max_time

    def get_step(self) -> int:
        return self._step

    # --- Fluent setters ---------------------------------------------------

    def min_time(self, value: str) -> "TimePicker":
        self._min_time = value
        return self

    def max_time(self, value: str) -> "TimePicker":
        self._max_time = value
        return self

    def step(self, seconds: int) -> "TimePicker":
        """Set the step increment in seconds (e.g. 900 for 15-minute intervals)."""
        self._step = seconds
        return self
