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
    # Layout hints — used when the field lives inside a Section
    col_span: int | str = 1   # 1 (default) | 2 | 3 | 4 | "full"
    is_section: bool = False  # discriminator — always False for fields

    def __post_init__(self):
        if not self.label:
            self.label = self.key.replace("_", " ").title()


@dataclass
class Section:
    """
    A layout container that groups fields into a responsive grid.

    Example::

        Section(
            title="Contact",
            cols=2,
            styled=True,
            fields=[
                Text(key="email"),
                Text(key="phone", col_span="full"),
            ],
            footer="All fields are required.",
        )
    """
    fields: list
    title: str = ""
    description: str = ""
    footer: str = ""
    cols: int = 1          # 1 | 2 | 3 | 4  (responsive breakpoints applied automatically)
    col_span: int | str = 1  # 1 | 2 | 3 | 4 | "full"
    styled: bool = True    # True = white card with border, shadow, optional header/footer
    is_section: bool = True  # discriminator — always True for sections


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
