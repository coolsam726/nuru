"""nuru.components — additional field types backed by Flowbite widgets."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from nuru.forms.base import Field
from nuru.forms.radio import Radio
from nuru.forms.toggle import Toggle
from nuru.forms.radio_buttons import RadioButtons
from nuru.forms.timepicker import TimePicker as Timepicker

if TYPE_CHECKING:
    from nuru.panel import AdminPanel


def register_components(panel: "AdminPanel") -> None:
    """Register component templates with *panel*. Call once during app setup."""
    # Templates have been moved into the main `nuru/templates` tree; nothing
    # to register here anymore. This function is kept for compatibility.
    return None


# The Flowbite-backed component field classes live in the `forms` package.
# Import them here to keep the `nuru.components` API surface stable.

# Radio, Toggle, RadioButtons: simple Flowbite-style input widgets
# Timepicker is exported as the historical `Timepicker` name for
# backwards-compatibility (the canonical class in `forms` is `TimePicker`).
