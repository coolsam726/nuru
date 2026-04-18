"""nuru.actions.base — Action base class and built-in action types."""

from __future__ import annotations

import json
from typing import Any


_MISSING = object()

_STYLE_CLASSES: dict[str, str] = {
    "default":   ("border border-secondary-200 dark:border-secondary-600 "
                  "text-secondary-700 dark:text-secondary-300 "
                  "hover:bg-secondary-50 dark:hover:bg-secondary-700"),
    "secondary": ("border border-secondary-300 dark:border-secondary-600 "
                  "text-secondary-500 dark:text-secondary-400 "
                  "hover:bg-secondary-50 dark:hover:bg-secondary-700"),
    "primary":   "text-white bg-primary hover:bg-primary-600",
    "success":   ("border border-green-200 dark:border-green-700/50 "
                  "text-green-700 dark:text-green-400 "
                  "hover:bg-green-50 dark:hover:bg-green-900/30"),
    "warning":   ("border border-amber-200 dark:border-amber-700/50 "
                  "text-amber-700 dark:text-amber-400 "
                  "hover:bg-amber-50 dark:hover:bg-amber-900/30"),
    "danger":    ("border border-red-200 dark:border-red-700/50 "
                  "text-red-700 dark:text-red-400 "
                  "hover:bg-red-50 dark:hover:bg-red-900/30"),
}


class Action:
    """
    A server-side action button usable in any context:
    row actions, form header, page header, bulk actions.

    All state is private; public access is via fluent setters (return self)
    and no-arg getter calls.

    Usage::

        Action.make("send_email")
            .label("Send Welcome Email")
            .icon("envelope")
            .style("primary")
            .confirm("Send email to this user?")
            .fields([Text("subject").required()])
            .handler("send_welcome")
    """

    # Sentinels for built-in actions (handled by the framework directly).
    KEY_VIEW   = "__view__"
    KEY_EDIT   = "__edit__"
    KEY_DELETE = "__delete__"
    KEY_CREATE = "__create__"

    def __init__(self, key: str) -> None:
        self._key: str = key
        self._label: str = key.replace("_", " ").title()
        self._icon: str = ""
        self._style: str = "default"
        self._confirm: str = ""
        self._fields: list[Any] = []
        self._handler: str = ""
        self._placement: str = "row"   # "row" | "header" | "bulk"
        self._modal_title: str = ""
        self._is_builtin: bool = False
        self._submit_label: str = ""

    # ------------------------------------------------------------------ #
    # Factory                                                              #
    # ------------------------------------------------------------------ #

    @classmethod
    def make(cls, key: str) -> "Action":
        return cls(key)

    # ------------------------------------------------------------------ #
    # Properties — template-friendly attribute access (no get_ prefix)    #
    # ------------------------------------------------------------------ #

    @property
    def key(self) -> str: return self._key

    @property
    def label(self) -> str: return self._label

    @property
    def icon(self) -> str: return self._icon

    @property
    def style(self) -> str: return self._style

    @property
    def confirm(self) -> str: return self._confirm

    @property
    def is_builtin(self) -> bool: return self._is_builtin

    @property
    def modal_title(self) -> str: return self._modal_title or self._label

    @property
    def handler(self) -> str: return self._handler

    # ------------------------------------------------------------------ #
    # Getters (no-arg calls)                                              #
    # ------------------------------------------------------------------ #

    def get_key(self) -> str:
        return self._key

    def get_label(self) -> str:
        return self._label

    def get_icon(self) -> str:
        return self._icon

    def get_style(self) -> str:
        return self._style

    def get_confirm(self) -> str:
        return self._confirm

    def get_fields(self) -> list[Any]:
        return list(self._fields)

    def get_handler(self) -> str:
        return self._handler

    def get_placement(self) -> str:
        return self._placement

    def get_modal_title(self) -> str:
        return self._modal_title or self._label


    def get_submit_label(self) -> str:
        return self._submit_label or self._label

    def get_style_classes(self) -> str:
        return _STYLE_CLASSES.get(self._style, _STYLE_CLASSES["default"])

    # ------------------------------------------------------------------ #
    # Fluent setters — use set_* names to avoid collision with properties  #
    # ------------------------------------------------------------------ #

    def set_label(self, value: str) -> "Action":
        self._label = value; return self

    def set_icon(self, value: str) -> "Action":
        self._icon = value; return self

    def set_style(self, value: str) -> "Action":
        self._style = value; return self

    def set_confirm(self, value: str) -> "Action":
        self._confirm = value; return self

    def fields(self, value: list[Any]) -> "Action":
        self._fields = list(value)
        return self

    def set_handler(self, value: str) -> "Action":
        self._handler = value; return self

    def handler(self, value: str) -> "Action":
        self._handler = value
        return self

    def set_placement(self, value: str) -> "Action":
        self._placement = value; return self

    def placement(self, value: str) -> "Action":
        self._placement = value
        return self

    def set_modal_title(self, value: str) -> "Action":
        self._modal_title = value; return self

    def modal_title(self, value: str) -> "Action":
        self._modal_title = value
        return self

    def set_submit_label(self, value: str) -> "Action":
        self._submit_label = value; return self

    def submit_label(self, value: str) -> "Action":
        self._submit_label = value
        return self

    # ------------------------------------------------------------------ #
    # Template helpers                                                     #
    # ------------------------------------------------------------------ #

    def fields_json(self) -> str:
        """Serialize action fields to JSON for the modal data-attribute."""
        out = []
        for f in self._fields:
            out.append({
                "key":         getattr(f, "_key", ""),
                "label":       getattr(f, "_label", ""),
                "field_type":  getattr(f, "_field_type", "text"),
                "input_type":  getattr(f, "_input_type", "text"),
                "required":    getattr(f, "_required", False),
                "placeholder": getattr(f, "_placeholder", ""),
                "help_text":   getattr(f, "_help_text", ""),
            })
        return json.dumps(out)

    def __repr__(self) -> str:
        return f"Action(key={self._key!r}, label={self._label!r}, style={self._style!r})"


# ------------------------------------------------------------------ #
# Built-in action singletons                                           #
# ------------------------------------------------------------------ #

class _BuiltinAction(Action):
    def __init__(self, key: str, label: str, icon: str, style: str = "default") -> None:
        super().__init__(key)
        self._label = label
        self._icon = icon
        self._style = style
        self._is_builtin = True


class ViewAction(_BuiltinAction):
    def __init__(self) -> None:
        super().__init__(
            Action.KEY_VIEW, "View",
            "M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z",
            "default",
        )


class EditAction(_BuiltinAction):
    def __init__(self) -> None:
        super().__init__(
            Action.KEY_EDIT, "Edit",
            "M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z",
            "default",
        )


class DeleteAction(_BuiltinAction):
    def __init__(self) -> None:
        super().__init__(
            Action.KEY_DELETE, "Delete",
            "M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16",
            "danger",
        )


class CreateAction(_BuiltinAction):
    def __init__(self) -> None:
        super().__init__(
            Action.KEY_CREATE, "Create",
            "M12 4v16m8-8H4",
            "primary",
        )

