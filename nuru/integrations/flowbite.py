"""nuru × Flowbite Datepicker integration."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from nuru.forms.datepicker import DatePicker
from nuru.forms.datetimepicker import DateTimePicker
from nuru.forms.timepicker import TimePicker

if TYPE_CHECKING:
    from nuru.panel import AdminPanel

FLOWBITE_JS_CDN = "https://cdn.jsdelivr.net/npm/flowbite@4.0.1/dist/flowbite.min.js"
_TEMPLATES_DIR = Path(__file__).parent / "flowbite_templates"


class FlowbiteDatepicker(DatePicker):
    """Single-date Flowbite datepicker field.

    .. deprecated::
        Use :class:`nuru.forms.DatePicker` directly.
        ``FlowbiteDatepicker`` is kept for backward compatibility.
    """

    _FIELD_TYPE = "flowbite_datepicker"


class FlowbiteDateRangePicker(DatePicker):
    """Date-range Flowbite picker: two inputs (start + end) in one field.

    .. deprecated::
        Prefer :class:`DateRangePicker` going forward.
        ``FlowbiteDateRangePicker`` is kept for backward compatibility.
    """

    _FIELD_TYPE = "flowbite_daterangepicker"

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._start_placeholder: str = "Start date"
        self._end_placeholder: str = "End date"

    def get_start_placeholder(self) -> str:
        return self._start_placeholder

    def get_end_placeholder(self) -> str:
        return self._end_placeholder

    def start_placeholder(self, value: str) -> "FlowbiteDateRangePicker":
        self._start_placeholder = value
        return self

    def end_placeholder(self, value: str) -> "FlowbiteDateRangePicker":
        self._end_placeholder = value
        return self


class DateRangePicker(FlowbiteDateRangePicker):
    """Date-range picker: two Flowbite datepicker inputs (start + end).

    Example::

        DateRangePicker("stay").label("Stay dates")
        DateRangePicker("period").label("Period").start_placeholder("From").end_placeholder("To")
    """

    _FIELD_TYPE = "flowbite_daterangepicker"  # reuses the same template


def register_flowbite(panel: "AdminPanel") -> None:
    """Register the Flowbite integration with *panel*."""
    panel.add_template_dir(_TEMPLATES_DIR)
    panel.add_extra_js(FLOWBITE_JS_CDN)
