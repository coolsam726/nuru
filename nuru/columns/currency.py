"""nuru.columns.currency — monetary value column."""
from __future__ import annotations
from typing import Any
from .base import Column


class Currency(Column):
    """Renders a numeric value as formatted currency."""

    _COLUMN_TYPE = "currency"

    def __init__(self, key: str, label: str = "", sortable: bool = False,
                 currency: str = "USD", decimals: int = 2) -> None:
        super().__init__(key, label, sortable)
        self._currency = currency
        self._decimals = decimals

    def currency(self, value: str) -> "Currency":   # type: ignore[override]
        self._currency = value; return self

    def decimals(self, value: int) -> "Currency":
        self._decimals = value; return self

    def get_currency(self) -> str: return self._currency
    def get_decimals(self) -> int: return self._decimals

    def render(self, value: Any) -> str:
        if value is None or value == "":
            return "—"
        try:
            return f"{self._currency} {float(value):,.{self._decimals}f}"
        except (ValueError, TypeError):
            return str(value)

