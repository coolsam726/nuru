from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Field:
    key: str
    label: str = ""
    required: bool = False
    placeholder: str = ""
    help_text: str = ""
    default: Any = None
    field_type: str = "text"
    input_type: str = "text"

    def __post_init__(self):
        if not self.label:
            self.label = self.key.replace("_", " ").title()


@dataclass
class Text(Field):
    field_type: str = "text"
    input_type: str = "text"
    max_length: int | None = None


@dataclass
class Email(Field):
    field_type: str = "text"
    input_type: str = "email"


@dataclass
class Password(Field):
    field_type: str = "text"
    input_type: str = "password"


@dataclass
class Number(Field):
    field_type: str = "text"
    input_type: str = "number"
    min_value: float | None = None
    max_value: float | None = None


@dataclass
class Textarea(Field):
    field_type: str = "textarea"
    input_type: str = "textarea"
    rows: int = 4


@dataclass
class Select(Field):
    field_type: str = "select"
    input_type: str = "select"
    options: list = field(default_factory=list)


@dataclass
class Checkbox(Field):
    field_type: str = "checkbox"
    input_type: str = "checkbox"


@dataclass
class Date(Field):
    field_type: str = "text"
    input_type: str = "date"


@dataclass
class Time(Field):
    field_type: str = "text"
    input_type: str = "time"


@dataclass
class Hidden(Field):
    field_type: str = "hidden"
    input_type: str = "hidden"
