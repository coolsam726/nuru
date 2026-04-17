"""nuru.forms.base — base Field class.

All field types inherit from :class:`Field`.  Internal state is stored on
``_`` -prefixed instance variables.  The public API consists of:

* **Fluent setters** — mutate the field in-place and return ``self`` so calls
  can be chained::

      Text("email").label("E-mail").required().placeholder("you@example.com")

* **Getter methods** — read internal state::

      field.get_label()     # str
      field.is_required()   # bool
"""

from __future__ import annotations

from typing import Any


class Field:
    """Base class for all Nuru form and detail fields."""

    # ------------------------------------------------------------------ #
    # Class-level defaults — overridden by subclasses.                    #
    # ------------------------------------------------------------------ #
    _FIELD_TYPE: str = "text"
    _INPUT_TYPE: str = "text"

    # ------------------------------------------------------------------ #
    # Construction                                                         #
    # ------------------------------------------------------------------ #

    def __init__(self, key: str) -> None:
        self._key: str = key
        self._label: str = key.replace("_", " ").title()
        self._field_type: str = self._FIELD_TYPE
        self._input_type: str = self._INPUT_TYPE

        # Value constraints / meta
        self._required: bool = False
        self._placeholder: str = ""
        self._help_text: str = ""
        self._default: Any = None
        self._validators: list[str] = []

        # Input element styling
        self._input_class: str = ""
        self._input_style: str = ""

        # Layout hints (used inside Section containers)
        self._col_span: int | str = 1
        self._css_class: str = ""
        self._cols: int = 1
        self._styled: bool = False

        # Accessibility
        self._disabled: bool = False
        self._readonly: bool = False
        self._visible: bool = True
        self._autofocus: bool = False
        self._autocomplete: str = ""

        # Filament-style addons
        self._nullable: bool = False
        self._reactive: bool = False
        self._prefix: str = ""
        self._suffix: str = ""
        self._prefix_icon: str = ""
        self._suffix_icon: str = ""

    # ------------------------------------------------------------------ #
    # Identity discriminator                                              #
    # ------------------------------------------------------------------ #

    def is_section_field(self) -> bool:
        """Return ``False`` for fields; ``True`` only for Section/Fieldset."""
        return False

    # ------------------------------------------------------------------ #
    # Getters                                                              #
    # ------------------------------------------------------------------ #

    def get_key(self) -> str:
        return self._key

    def get_label(self) -> str:
        return self._label

    def get_field_type(self) -> str:
        return self._field_type

    def get_input_type(self) -> str:
        return self._input_type

    def is_required(self) -> bool:
        return self._required

    def get_placeholder(self) -> str:
        return self._placeholder

    def get_help_text(self) -> str:
        return self._help_text

    def get_default(self) -> Any:
        return self._default

    def get_validators(self) -> list[str]:
        return list(self._validators)

    def get_input_class(self) -> str:
        return self._input_class

    def get_input_style(self) -> str:
        return self._input_style

    def get_col_span(self) -> int | str:
        return self._col_span

    def get_css_class(self) -> str:
        return self._css_class

    def get_cols(self) -> int:
        return self._cols

    def is_styled(self) -> bool:
        return self._styled

    def is_disabled(self) -> bool:
        return self._disabled

    def is_readonly(self) -> bool:
        return self._readonly

    def is_visible(self) -> bool:
        return self._visible

    def is_autofocus(self) -> bool:
        return self._autofocus

    def get_autocomplete(self) -> str:
        return self._autocomplete

    def is_nullable(self) -> bool:
        return self._nullable

    def is_reactive(self) -> bool:
        return self._reactive

    def get_prefix(self) -> str:
        return self._prefix

    def get_suffix(self) -> str:
        return self._suffix

    def get_prefix_icon(self) -> str:
        return self._prefix_icon

    def get_suffix_icon(self) -> str:
        return self._suffix_icon

    # ------------------------------------------------------------------ #
    # Fluent setters — all return ``self`` for chaining                   #
    # ------------------------------------------------------------------ #

    def label(self, value: str) -> "Field":
        """Set the human-readable label shown above the input."""
        self._label = value
        return self

    def title(self, value: str) -> "Field":
        """Alias for :meth:`label`."""
        return self.label(value)

    def required(self, on: bool = True) -> "Field":
        """Mark the field as required (shows a ``*`` marker)."""
        self._required = on
        return self

    def optional(self) -> "Field":
        """Mark the field as optional (opposite of :meth:`required`)."""
        return self.required(False)

    def placeholder(self, value: str) -> "Field":
        self._placeholder = value
        return self

    def help_text(self, value: str) -> "Field":
        self._help_text = value
        return self

    def hint(self, value: str) -> "Field":
        """Alias for :meth:`help_text`."""
        return self.help_text(value)

    def default(self, value: Any) -> "Field":
        self._default = value
        return self

    def add_validator(self, name: str) -> "Field":
        self._validators = list(self._validators) + [name]
        return self

    def input_class(self, value: str) -> "Field":
        self._input_class = value
        return self

    def input_style(self, value: str) -> "Field":
        self._input_style = value
        return self

    def col_span(self, value: int | str) -> "Field":
        self._col_span = value
        return self

    def css_class(self, value: str) -> "Field":
        self._css_class = value
        return self

    def cols(self, value: int) -> "Field":
        self._cols = value
        return self

    def styled(self, on: bool = True) -> "Field":
        self._styled = on
        return self

    def disabled(self, on: bool = True) -> "Field":
        self._disabled = on
        return self

    def readonly(self, on: bool = True) -> "Field":
        self._readonly = on
        return self

    def visible(self, on: bool = True) -> "Field":
        self._visible = on
        return self

    def hidden(self) -> "Field":
        """Hide the field from the UI."""
        return self.visible(False)

    def autofocus(self, on: bool = True) -> "Field":
        self._autofocus = on
        return self

    def autocomplete(self, value: str) -> "Field":
        self._autocomplete = value
        return self

    def nullable(self, on: bool = True) -> "Field":
        self._nullable = on
        return self

    def reactive(self, on: bool = True) -> "Field":
        self._reactive = on
        return self

    def prefix(self, value: str) -> "Field":
        self._prefix = value
        return self

    def suffix(self, value: str) -> "Field":
        self._suffix = value
        return self

    def prefix_icon(self, name: str) -> "Field":
        self._prefix_icon = name
        return self

    def suffix_icon(self, name: str) -> "Field":
        self._suffix_icon = name
        return self

    # ------------------------------------------------------------------ #
    # Input-type / validator convenience methods                          #
    # ------------------------------------------------------------------ #

    def email(self) -> "Field":
        self._input_type = "email"
        return self.add_validator("email")

    def numeric(self) -> "Field":
        return self.add_validator("numeric")

    def integer(self) -> "Field":
        return self.add_validator("integer")

    def password(self) -> "Field":
        self._input_type = "password"
        return self

    def tel(self) -> "Field":
        self._input_type = "tel"
        return self

    def url(self) -> "Field":
        self._input_type = "url"
        return self.add_validator("url")

    def max_length(self, n: int) -> "Field":
        self._max_length = n
        return self

    def get_max_length(self) -> int | None:
        return getattr(self, "_max_length", None)

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(key={self._key!r}, "
            f"label={self._label!r}, "
            f"required={self._required})"
        )
