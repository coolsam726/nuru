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


@dataclass
class Image(Column):
    """Render a stored file server-ID (relative path) as a circular thumbnail.

    Args:
        url_prefix: URL prefix that, combined with the stored value, gives the
            full public URL of the image.  Defaults to the empty string — in
            that case you must pass an absolute URL or configure the prefix
            at build time.
        size: Tailwind size token applied to ``w-*`` and ``h-*`` (default ``8``
            → 32 px).
        rounded: CSS class for the shape (default ``rounded-full`` = circle).
        placeholder_icon: SVG path data to use when no image is stored.
    """
    url_prefix: str = ""
    size: str = "8"
    rounded: str = "rounded-full"
    # Default placeholder: a simple person silhouette path
    placeholder_icon: str = (
        "M16 7a4 4 0 11-8 0 4 4 0 018 0z"
        "M12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
    )

    def get_url(self, value: Any) -> str | None:
        """Return the absolute URL for *value*, or None when empty."""
        if not value or str(value).strip() == "":
            return None
        v = str(value).strip()
        if v.startswith(("http://", "https://", "/")):
            return v
        prefix = self.url_prefix.rstrip("/")
        return f"{prefix}/{v}"

