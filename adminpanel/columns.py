from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Column:
    key: str
    label: str = ""
    sortable: bool = False

    def __post_init__(self):
        if not self.label:
            self.label = self.key.replace("_", " ").title()

    def render(self, value: Any) -> str:
        if value is None or value == "":
            return "—"
        return str(value)


@dataclass
class Text(Column):
    max_length: int | None = None

    def render(self, value: Any) -> str:
        if value is None or value == "":
            return "—"
        s = str(value)
        if self.max_length and len(s) > self.max_length:
            return s[:self.max_length] + "…"
        return s


@dataclass
class Badge(Column):
    colors: dict[str, str] = field(default_factory=dict)

    _COLOR_CLASSES = {
        "green":  "bg-green-100 text-green-800",
        "red":    "bg-red-100 text-red-800",
        "amber":  "bg-amber-100 text-amber-800",
        "blue":   "bg-blue-100 text-blue-800",
        "purple": "bg-purple-100 text-purple-800",
        "pink":   "bg-pink-100 text-pink-800",
        "gray":   "bg-slate-100 text-slate-700",
    }

    def css_classes(self, value: Any) -> str:
        color = self.colors.get(str(value), "gray")
        return self._COLOR_CLASSES.get(color, self._COLOR_CLASSES["gray"])

    def render(self, value: Any) -> str:
        if value is None or value == "":
            return "—"
        return str(value)


@dataclass
class Currency(Column):
    currency: str = "USD"
    decimals: int = 2

    def render(self, value: Any) -> str:
        if value is None or value == "":
            return "—"
        try:
            return f"{self.currency} {float(value):,.{self.decimals}f}"
        except (ValueError, TypeError):
            return str(value)


@dataclass
class DateTime(Column):
    fmt: str = "%d %b %Y, %H:%M"
    date_only: bool = False

    def render(self, value: Any) -> str:
        if value is None or value == "":
            return "—"
        from datetime import datetime, date
        fmt = "%d %b %Y" if self.date_only else self.fmt
        if isinstance(value, (datetime, date)):
            return value.strftime(fmt)
        try:
            return datetime.fromisoformat(str(value)).strftime(fmt)
        except (ValueError, TypeError):
            return str(value)


@dataclass
class Boolean(Column):
    true_label: str = "Yes"
    false_label: str = "No"

    def render(self, value: Any) -> str:
        return self.true_label if value else self.false_label

    def is_true(self, value: Any) -> bool:
        return bool(value)
