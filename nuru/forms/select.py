"""nuru.forms.select — select / combobox field."""

from __future__ import annotations

from typing import Any, Callable

from .field_base import Field


class Select(Field):
    """Versatile select / combobox field.

    **Static options**::

        Select("status").options(["draft", "published"])
        Select("status").options([{"value": "1", "label": "Active"}, …])

    **Multiple selection** (submits as a list)::

        Select("tags").multiple().options([…])

    **Model-backed combobox** (queries a SQLModel class directly)::

        Select("author_id").label("Author").model(Author, value_field="id", label_field="name")

    **Native ``<select>``** (instead of the combobox widget)::

        Select("status").native().options([…])
    """

    _FIELD_TYPE = "select"
    _INPUT_TYPE = "select"

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self._options: list | Callable[[Any], list[dict]] = []
        self._multiple: bool = False
        self._native: bool = False
        self._remote_search: bool = False
        # Model-backed relationship
        self._model: Any = None
        self._value_field: str = ""
        self._label_field: str = ""
        self._search_fields: list[str] = []
        self._relationship: str = ""

    # --- Getters ----------------------------------------------------------

    def get_options(self) -> list | Callable:
        return self._options

    def is_multiple(self) -> bool:
        return self._multiple

    def is_native(self) -> bool:
        return self._native

    def is_remote_search(self) -> bool:
        return self._remote_search

    def get_model(self) -> Any:
        return self._model

    def get_value_field(self) -> str:
        return self._value_field

    def get_label_field(self) -> str:
        return self._label_field

    def get_search_fields(self) -> list[str]:
        return list(self._search_fields)

    def get_relationship(self) -> str:
        return self._relationship

    # --- Fluent setters ---------------------------------------------------

    def options(self, value: list | Callable) -> "Select":
        self._options = value
        return self

    def multiple(self, on: bool = True) -> "Select":
        self._multiple = on
        return self

    def native(self, on: bool = True) -> "Select":
        self._native = on
        return self

    def remote_search(self, on: bool = True) -> "Select":
        self._remote_search = on
        return self

    def model(
        self,
        model_class: Any,
        *,
        value_field: str = "",
        label_field: str = "",
        search_fields: list[str] | None = None,
    ) -> "Select":
        self._model = model_class
        self._value_field = value_field
        self._label_field = label_field
        self._search_fields = search_fields or []
        return self

    def relationship(self, attr: str) -> "Select":
        self._relationship = attr
        return self

    def value_field(self, value: str) -> "Select":
        self._value_field = value
        return self

    def label_field(self, value: str) -> "Select":
        self._label_field = value
        return self
