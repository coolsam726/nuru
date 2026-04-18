"""nuru.forms.section — layout containers (Section, Fieldset).

Sections and Fieldsets group fields into responsive grids.  They are not
fields themselves — ``is_section_field()`` returns ``True`` — but they share
the same slot in ``form_fields`` / ``detail_fields`` lists.
"""

from __future__ import annotations

from typing import Any


class Section:
    """Groups fields into a responsive grid with an optional title and footer.

    Example::

        Section(
            title="Contact details",
            cols=2,
            fields=[
                Text("email").label("E-mail").required(),
                Text("phone").label("Phone"),
            ],
        )

    Fluent style::

        Section(fields=[…]).title("Contact").cols(2).styled()
    """

    def __init__(
        self,
        fields: list,
        *,
        title: str = "",
        description: str = "",
        footer: str = "",
        cols: int = 1,
        col_span: int | str = 1,
        css_class: str = "",
        styled: bool = True,
    ) -> None:
        self._fields: list = list(fields)
        self._title: str = title
        self._description: str = description
        self._footer: str = footer
        self._cols: int = cols
        self._col_span: int | str = col_span
        self._css_class: str = css_class
        self._styled: bool = styled

    @classmethod
    def make(cls, fields: list | None = None) -> "Section":
        """Factory-style constructor to match :class:`Field.make`.

        Example: ``Section.make([...]).title("Contact")``
        """
        obj = cls(fields or [])
        setattr(obj, "_factory", True)
        return obj
    # ------------------------------------------------------------------ #
    # Identity discriminator                                              #
    # ------------------------------------------------------------------ #

    def is_section_field(self) -> bool:
        return True

    def is_fieldset(self) -> bool:
        return False

    # ------------------------------------------------------------------ #
    # Getters                                                              #
    # ------------------------------------------------------------------ #

    def get_fields(self) -> list:
        return list(self._fields)

    def get_title(self) -> str:
        return self._title

    def get_description(self) -> str:
        return self._description

    def get_footer(self) -> str:
        return self._footer

    def get_cols(self) -> int:
        return self._cols

    def get_col_span(self) -> int | str:
        return self._col_span

    def get_css_class(self) -> str:
        return self._css_class

    def is_styled(self) -> bool:
        return self._styled

    def get_section_type(self) -> str:
        return "styled" if self._styled else "flat"

    # ------------------------------------------------------------------ #
    # Fluent setters                                                       #
    # ------------------------------------------------------------------ #

    def title(self, value: str) -> "Section":
        self._title = value
        return self

    def description(self, value: str) -> "Section":
        self._description = value
        return self

    def footer(self, value: str) -> "Section":
        self._footer = value
        return self

    def cols(self, n: int) -> "Section":
        self._cols = n
        return self

    def col_span(self, value: int | str) -> "Section":
        self._col_span = value
        return self

    def css_class(self, value: str) -> "Section":
        self._css_class = value
        return self

    def styled(self, on: bool = True) -> "Section":
        self._styled = on
        return self

    # Allow iteration so existing template code that does ``for f in section``
    # still works during gradual migration.
    @property
    def fields(self) -> list:
        return self._fields

    def __repr__(self) -> str:
        return f"Section(title={self._title!r}, fields={len(self._fields)})"


class Fieldset(Section):
    """Semantic ``<fieldset>`` with a floating ``<legend>``.

    Renders as a bordered box with the title in the border on form pages, and
    as a titled card on detail pages.

    Example::

        Fieldset(
            title="Billing address",
            cols=2,
            fields=[
                Text("street"),
                Text("city"),
                Text("postcode").col_span("full"),
            ],
        )
    """

    def is_fieldset(self) -> bool:
        return True

    def get_section_type(self) -> str:
        return "fieldset"
