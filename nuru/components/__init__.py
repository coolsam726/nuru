from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from .types import RadioOption

from nuru.fields import Field
from nuru.panel import AdminPanel


def register_components(panel: "AdminPanel") -> None:
    """Register the components' templates with the provided AdminPanel.

    Call once during app setup (similar to ``register_flowbite``).
    """
    panel.add_template_dir(Path(__file__).parent / "templates")




@dataclass
class Radio(Field):
    field_type: str = "radio"
    input_type: str = "radio"
    options: list[RadioOption | tuple | str] = field(default_factory=list)
    inline: bool = True




@dataclass
class Toggle(Field):
    """Boolean toggle rendered as a Flowbite-style switch.

    Uses an underlying checkbox input for form submission.
    """
    field_type: str = "toggle"
    input_type: str = "checkbox"
    on_label: str = "On"
    off_label: str = "Off"




@dataclass
class RadioButtons(Field):
    """Group of radio buttons rendered as pill-like choices."""
    field_type: str = "radio_buttons"
    input_type: str = "radio"
    options: list[RadioOption | tuple | str] = field(default_factory=list)




@dataclass
class Timepicker(Field):
    """Simple timepicker backed by a text input. Format defaults to HH:MM."""
    field_type: str = "timepicker"
    input_type: str = "text"
    time_format: str = "HH:MM"
    placeholder: str = "HH:MM"



__all__ = ["register_components", "Radio", "Toggle", "RadioButtons", "Timepicker"]


