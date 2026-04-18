"""nuru.columns — table column classes.

Usage::

    from nuru.columns import Text, Badge, Boolean, Currency, DateTime, Image

All columns support positional construction AND a fluent make() API::

    # positional (legacy style)
    Text("name", "Full Name", sortable=True)

    # fluent
    Text.make("name").label("Full Name").sortable()
"""
from .base import Column
from .text import Text
from .badge import Badge
from .currency import Currency
from .datetime import DateTime
from .boolean import Boolean
from .image import Image

__all__ = [
    "Column",
    "Text",
    "Badge",
    "Currency",
    "DateTime",
    "Boolean",
    "Image",
]

