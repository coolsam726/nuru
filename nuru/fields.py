from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, List


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
    css_class: str = ""       # extra Tailwind classes applied to the field wrapper
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
    css_class: str = ""    # extra Tailwind classes applied to the outer wrapper
    styled: bool = True    # True = white card with border, shadow, optional header/footer
    section_type: str = ""  # derived automatically; override to select a custom partial
    is_section: bool = True  # discriminator
    is_fieldset: bool = False

    def __post_init__(self):
        if not self.section_type:
            self.section_type = "styled" if self.styled else "flat"


@dataclass
class Fieldset:
    """
    A semantic ``<fieldset>`` grouping with a ``<legend>`` label.

    Visually renders as a bordered box with the title floating in the border.
    On detail pages it renders as a titled card, same as a styled Section.

    Example::

        Fieldset(
            title="Billing Address",
            cols=2,
            fields=[
                Text(key="street"),
                Text(key="city"),
                Text(key="postcode", col_span="full"),
            ],
        )
    """
    fields: list
    title: str = ""
    description: str = ""
    cols: int = 1
    col_span: int | str = 1
    css_class: str = ""   # extra Tailwind classes applied to the <fieldset> element
    section_type: str = "fieldset"  # override to select a custom partial
    is_section: bool = True   # enters the same template branch as Section
    is_fieldset: bool = True  # selects <fieldset>/<legend> rendering


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
    """Versatile select / combobox field.

    **Static options** — pass a list of strings or ``{"value": ..., "label": ...}``
    dicts::

        Select("status", options=["draft", "published", "archived"])
        Select("status", options=[{"value": "1", "label": "Active"}, ...])

    **Multiple** — allow picking several values (submits as a list)::

        Select("tags", multiple=True, options=[...])

    **Relationship (model-based combobox)** — point directly at a SQLModel class;
    the panel queries the model via a built-in ``/_model_search`` endpoint without
    requiring a matching Resource to exist::

        Select("author_id", "Author",
               model=Author,           # SQLModel class reference
               value_field="id",       # attr used as the FK value (default: model PK)
               label_field="name",     # attr shown as the option label
               relationship="author")  # attr on *this* record holding the pre-loaded
                                       # relation — used for display in the detail view

    ``search_fields`` lists additional model columns to include in the server-side
    ``ilike`` search; ``label_field`` is always searched.

    **Detail view display** — set ``relationship`` to the pre-loaded relation
    attribute on your record so the human-readable label is shown instead of
    the raw FK value::

        # record.author.name is rendered in the detail view
        Select("author_id", label_field="name", relationship="author")
    """
    field_type: str = "select"
    input_type: str = "select"
    options: list|Callable[[Any], list[dict[str, str]]] = field(default_factory=list)
    multiple: bool = False
    # ── Relationship combobox ────────────────────────────────────────────
    model: Any = None               # SQLModel class to query directly
    value_field: str = ""           # attr used as option value (defaults to model PK)
    label_field: str = ""           # attr used as option label (defaults to str(record))
    search_fields: list = field(default_factory=list)  # extra columns for ilike search
    relationship: str = ""          # attr on *this* record holding the pre-loaded relation
    native: bool = False             # when True, render a native <select> instead of the combobox
    # `options` may be a static list or a callable that returns a list of
    # {"value":..., "label":...} dicts. If callable, it will be invoked
    # at render time to produce the initial option set.
    remote_search: bool = False     # fetch with ?q=<query> on each keystroke instead of
                                    # loading all options upfront and filtering client-side


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


@dataclass
class CheckboxGroup(Field):
    """Multi-select field rendered as clickable pill/tag buttons.

    ``options`` — list of ``{value, label}`` dicts or plain strings.
    ``options_attr`` — if set, options are read from ``record.<options_attr>``
    at render time (dynamic choices set in ``get_record``).

    The form submits one checkbox value per selected option under the same
    ``name``. ``parse_form`` collects these into a Python list.
    """
    field_type: str = "checkbox_group"
    input_type: str = "checkbox_group"
    options: list = field(default_factory=list)
    options_attr: str = ""


# ---------------------------------------------------------------------------
# Flowbite-backed aliases
# If the Flowbite integration is present we prefer its Field dataclasses so
# users can `from nuru.fields import Datepicker` and get the Flowbite
# implementation. Fall back to lightweight local dataclasses when the
# integration isn't available (keeps imports safe for minimal installs).
try:
    from nuru.integrations.flowbite import FlowbiteDatepicker as Datepicker  # type: ignore
    from nuru.integrations.flowbite import FlowbiteDateRangePicker as DateRangePicker  # type: ignore
    from nuru.components import register_components  # type: ignore
    from nuru.components import Radio, Toggle, RadioButtons, Timepicker  # type: ignore
except Exception:
    @dataclass
    class Datepicker(Field):
        field_type: str = "flowbite_datepicker"
        input_type: str = "text"
        date_format: str = "yyyy-mm-dd"
        autohide: bool = True
        buttons: bool = False
        orientation: str = "bottom"
        title: str = ""
        min_date: str = ""
        max_date: str = ""


    @dataclass
    class DateRangePicker(Field):
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

    @dataclass
    class Radio(Field):
        field_type: str = "radio"
        input_type: str = "radio"
        options: list = field(default_factory=list)
        inline: bool = True
        
    @dataclass
    class Toggle(Field):
        field_type: str = "toggle"
        input_type: str = "checkbox"
        on_label: str = "On"
        off_label: str = "Off"
        
    @dataclass
    class RadioButtons(Field):
        field_type: str = "radio_buttons"
        input_type: str = "radio"
        options: list = field(default_factory=list)
        
    @dataclass
    class Timepicker(Field):
        field_type: str = "timepicker"
        input_type: str = "text"
        time_format: str = "HH:MM"
        placeholder: str = "HH:MM"

