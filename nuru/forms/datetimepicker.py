"""nuru.forms.datetimepicker — combined date + time picker field.

Renders a Flowbite datepicker alongside a native time input.
Requires ``register_flowbite(panel)`` to load the Flowbite JS CDN.
"""

from __future__ import annotations

from .field_base import Field


class DateTimePicker(Field):
    """Combined date + time picker.

    Submits two form values: ``{key}_date`` and ``{key}_time``.
    Override ``parse_form_data`` on the Resource to merge them if a single
    datetime string is needed.

    Example::

        DateTimePicker("event_at").label("Event date & time")
        DateTimePicker("scheduled").label("Scheduled").date_format("mm/dd/yyyy")
    """

    _FIELD_TYPE = "datetimepicker"
    _INPUT_TYPE = "text"

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._date_format: str = "yyyy-mm-dd"
        self._time_format: str = "HH:mm"
        self._autohide: bool = True
        self._buttons: bool = False
        self._orientation: str = "bottom"
        self._min_date: str = ""
        self._max_date: str = ""
        self._min_time: str = ""
        self._max_time: str = ""

    # --- Getters ----------------------------------------------------------

    def get_date_format(self) -> str:
        return self._date_format

    def get_time_format(self) -> str:
        return self._time_format

    def is_autohide(self) -> bool:
        return self._autohide

    def has_buttons(self) -> bool:
        return self._buttons

    def get_orientation(self) -> str:
        return self._orientation

    def get_min_date(self) -> str:
        return self._min_date

    def get_max_date(self) -> str:
        return self._max_date

    def get_min_time(self) -> str:
        return self._min_time

    def get_max_time(self) -> str:
        return self._max_time

    # --- Fluent setters ---------------------------------------------------

    def date_format(self, fmt: str) -> "DateTimePicker":
        self._date_format = fmt
        return self

    def time_format(self, fmt: str) -> "DateTimePicker":
        self._time_format = fmt
        return self

    def autohide(self, on: bool = True) -> "DateTimePicker":
        self._autohide = on
        return self

    def buttons(self, on: bool = True) -> "DateTimePicker":
        self._buttons = on
        return self

    def orientation(self, value: str) -> "DateTimePicker":
        self._orientation = value
        return self

    def min_date(self, value: str) -> "DateTimePicker":
        self._min_date = value
        return self

    def max_date(self, value: str) -> "DateTimePicker":
        self._max_date = value
        return self

    def min_time(self, value: str) -> "DateTimePicker":
        self._min_time = value
        return self

    def max_time(self, value: str) -> "DateTimePicker":
        self._max_time = value
        return self
