"""nuru.forms.datepicker — Flowbite-backed date picker field.

Requires ``register_flowbite(panel)`` to load the Flowbite JS CDN.
"""

from __future__ import annotations

from .field_base import Field


class DatePicker(Field):
    """Single-date picker backed by the Flowbite Datepicker widget.

    Example::

        DatePicker("birth_date").label("Date of Birth")
        DatePicker("expires").label("Expiry").date_format("mm/dd/yyyy").autohide(False)
        DatePicker("start").label("Start date").min_date("2024-01-01")
    """

    _FIELD_TYPE = "datepicker"
    _INPUT_TYPE = "text"

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._date_format: str = "yyyy-mm-dd"
        self._autohide: bool = True
        self._buttons: bool = False
        self._orientation: str = "bottom"
        self._picker_title: str = ""
        self._min_date: str = ""
        self._max_date: str = ""

    # --- Getters ----------------------------------------------------------

    def get_date_format(self) -> str:
        return self._date_format

    def is_autohide(self) -> bool:
        return self._autohide

    def has_buttons(self) -> bool:
        return self._buttons

    def get_orientation(self) -> str:
        return self._orientation

    def get_picker_title(self) -> str:
        return self._picker_title

    def get_min_date(self) -> str:
        return self._min_date

    def get_max_date(self) -> str:
        return self._max_date

    # --- Fluent setters ---------------------------------------------------

    def date_format(self, fmt: str) -> "DatePicker":
        self._date_format = fmt
        return self

    def autohide(self, on: bool = True) -> "DatePicker":
        self._autohide = on
        return self

    def buttons(self, on: bool = True) -> "DatePicker":
        self._buttons = on
        return self

    def orientation(self, value: str) -> "DatePicker":
        self._orientation = value
        return self

    def picker_title(self, value: str) -> "DatePicker":
        self._picker_title = value
        return self

    def min_date(self, value: str) -> "DatePicker":
        self._min_date = value
        return self

    def max_date(self, value: str) -> "DatePicker":
        self._max_date = value
        return self
