"""nuru.forms.checkbox_group — multi-select pill/tag group."""

from __future__ import annotations

from .field_base import Field


def _normalise_options(opts: list) -> list[dict]:
    out = []
    for item in opts:
        if isinstance(item, dict):
            out.append(item)
        elif isinstance(item, (tuple, list)) and len(item) == 2:
            out.append({"value": item[0], "label": item[1]})
        else:
            out.append({"value": item, "label": item})
    return out


class CheckboxGroup(Field):
    """Multi-select field rendered as clickable pill/tag buttons.

    The form submits one checkbox value per selected option under the same
    ``name`` key. ``parse_form`` collects these into a Python list.

    Example::

        CheckboxGroup("tags").label("Tags").options([
            {"value": "news", "label": "News"},
            {"value": "tech", "label": "Tech"},
        ])

    Dynamic options (resolved at render time from the record)::

        CheckboxGroup("permissions").options_from("available_permissions")
    """

    _FIELD_TYPE = "checkbox_group"
    _INPUT_TYPE = "checkbox_group"

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._options: list = []
        self._options_attr: str = ""

    # --- Getters ----------------------------------------------------------

    def get_options(self) -> list:
        return _normalise_options(self._options)

    def get_options_attr(self) -> str:
        return self._options_attr

    # --- Fluent setters ---------------------------------------------------

    def options(self, value: list) -> "CheckboxGroup":
        self._options = value
        return self

    def options_from(self, attr: str) -> "CheckboxGroup":
        """Read options from ``record.<attr>`` at render time."""
        self._options_attr = attr
        return self
