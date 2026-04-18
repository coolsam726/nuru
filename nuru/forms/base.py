"""nuru.forms.base — Form container class."""
from __future__ import annotations
from typing import Any

_MISSING = object()


class Form:
    """Reusable form container owning fields and actions."""

    def __init__(self) -> None:
        self._fields: list[Any] = []
        self._actions: list[Any] = []
        self._cols: int = 2
        self._title: str = ""

    @classmethod
    def make(cls, fields: list[Any] | None = None) -> "Form":
        obj = cls()
        if fields is not None:
            obj._fields = list(fields)
        return obj

    def fields(self, value=_MISSING):
        """Get all fields (no args) or set them (with list arg)."""
        if value is _MISSING:
            return list(self._fields)
        self._fields = list(value)
        return self

    def actions(self, value=_MISSING):
        """Get all actions (no args) or set them (with list arg)."""
        if value is _MISSING:
            return list(self._actions)
        self._actions = list(value)
        return self

    def schema(self, fields: list[Any]) -> "Form":
        self._fields = list(fields); return self

    def add_field(self, field: Any) -> "Form":
        self._fields.append(field); return self

    def add_action(self, action: Any) -> "Form":
        self._actions.append(action); return self

    def cols(self, value: int) -> "Form":
        self._cols = value; return self

    def title(self, value: str) -> "Form":
        self._title = value; return self

    def get_cols(self) -> int:
        return self._cols

    def get_title(self) -> str:
        return self._title

    def __repr__(self) -> str:
        return f"{type(self).__name__}(fields={len(self.fields())})"
