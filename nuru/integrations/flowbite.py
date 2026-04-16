"""
nuru × Flowbite Datepicker integration
=======================================

A standalone, opt-in module.  Import and call :func:`register_flowbite` once,
then use :class:`FlowbiteDatepicker` (and :class:`FlowbiteDateRangePicker`)
in any Resource ``form_fields`` / ``detail_fields`` / ``Page``.

Usage::

    from nuru import AdminPanel
    from nuru.integrations.flowbite import FlowbiteDatepicker, register_flowbite

    panel = AdminPanel(title="My App", prefix="/admin")
    register_flowbite(panel)   # loads CDN JS + registers templates

    class BookingResource(Resource):
        form_fields = [
            fields.Text("title", "Title"),
            FlowbiteDatepicker("check_in",  "Check-in",  required=True),
            FlowbiteDatepicker("check_out", "Check-out"),
        ]

Option sources
--------------
- ``date_format``    — format for both display **and** form submission.
  Default ``"yyyy-mm-dd"`` keeps ISO 8601 throughout so Python's date
  coercion in ``Resource.save_record()`` works without any extra setup.
- ``autohide``       — close the picker after a date is selected (default True).
- ``buttons``        — show *Today* / *Clear* action buttons (default False).
- ``min_date`` / ``max_date`` — restrict selectable range (``"yyyy-mm-dd"``).
- ``orientation``    — ``"bottom"`` | ``"top"`` | ``"bottom right"`` etc.
- ``title``          — optional header text shown inside the calendar popup.

Date range picker
-----------------
Use :class:`FlowbiteDateRangePicker` to collect a *start* + *end* date pair.
It renders as two inputs under a single label.  The submitted field names are
``{key}_start`` and ``{key}_end``::

    FlowbiteDateRangePicker("stay", "Stay dates")
    # → form data keys: stay_start, stay_end
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import TYPE_CHECKING

from nuru.fields import Field

if TYPE_CHECKING:
    from nuru.panel import AdminPanel

# CDN URL for Flowbite JS (includes auto-init for datepicker data attrs)
FLOWBITE_JS_CDN = "https://cdn.jsdelivr.net/npm/flowbite@4.0.1/dist/flowbite.min.js"

# Templates live next to this file
_TEMPLATES_DIR = Path(__file__).parent / "flowbite_templates"


# ---------------------------------------------------------------------------
# Field dataclasses
# ---------------------------------------------------------------------------

@dataclass
class FlowbiteDatepicker(Field):
    """Single-date Flowbite datepicker field.

    Renders a calendar popup triggered by an ``<input>`` with the Flowbite
    ``datepicker`` data attribute.  The submitted value is ISO ``yyyy-mm-dd``
    by default, compatible with nuru's built-in date coercion.
    """
    field_type: str = "flowbite_datepicker"
    input_type: str = "text"

    # Display / submission format understood by Flowbite datepicker.
    # Default is ISO 8601 so Python date coercion works without extra steps.
    date_format: str = "yyyy-mm-dd"

    # Picker behaviour
    autohide: bool = True
    buttons: bool = False
    orientation: str = "bottom"
    title: str = ""

    # Optional date range limits (use same format as date_format)
    min_date: str = ""
    max_date: str = ""


@dataclass
class FlowbiteDateRangePicker(Field):
    """Date-range Flowbite datepicker: two inputs (start + end) in one field.

    Submitted form keys are ``{key}_start`` and ``{key}_end``.
    """
    field_type: str = "flowbite_daterangepicker"
    input_type: str = "text"

    date_format: str = "yyyy-mm-dd"
    autohide: bool = True
    buttons: bool = False
    orientation: str = "bottom"
    title: str = ""

    min_date: str = ""
    max_date: str = ""

    start_placeholder: str = "Start date"
    end_placeholder: str = "End date"


# ---------------------------------------------------------------------------
# Registration helper
# ---------------------------------------------------------------------------

def register_flowbite(panel: "AdminPanel") -> None:
    """Register the Flowbite integration with *panel*.

    Idempotent — safe to call more than once with the same panel.

    What it does:

    1. Prepends the integration's ``flowbite_templates/`` directory to the
       panel's Jinja2 loader so ``partials/fields/form/flowbite_datepicker.html``
       and its detail counterpart are found automatically.
    2. Appends the Flowbite JS CDN ``<script>`` tag to every page rendered
       by this panel via the ``extra_js`` mechanism.
    """
    panel.add_template_dir(_TEMPLATES_DIR)
    panel.add_extra_js(FLOWBITE_JS_CDN)
