"""nuru.pages.base — Page base class and built-in page types."""
from __future__ import annotations
from typing import Any
class Page:
    """
    Base class for all Nuru pages (custom and built-in).
    Built-in pages (ListPage, CreatePage, EditPage, ViewPage) are registered
    automatically per resource by the Panel.
    Custom pages live in the panel's pages/ subdirectory and are
    auto-discovered on Panel.mount().
    Subclass style::
        class ReportsPage(Page):
            slug = "reports"
            title = "Reports"
            nav_icon = "chart-bar"
            def content(self, request) -> dict:
                return {"data": ...}
    make() inline style::
        Page.make().slug("reports").title("Reports")
    """
    slug: str = ""
    title: str = ""
    nav_icon: str = ""
    nav_sort: int = 100   # after resource nav items
    show_in_nav: bool = True
    def __init__(self) -> None:
        self._slug = self.__class__.slug
        self._title = self.__class__.title
        self._nav_icon = self.__class__.nav_icon
        self._nav_sort = self.__class__.nav_sort
        self._show_in_nav = self.__class__.show_in_nav
    @classmethod
    def make(cls) -> "Page":
        return cls()
    # Override in subclasses
    async def content(self, request: Any) -> dict:
        return {}
    # Fluent setters
    def slug(self, value: str) -> "Page":        # type: ignore[override]
        self._slug = value; return self
    def title(self, value: str) -> "Page":       # type: ignore[override]
        self._title = value; return self
    def nav_icon(self, value: str) -> "Page":    # type: ignore[override]
        self._nav_icon = value; return self
    def nav_sort(self, value: int) -> "Page":    # type: ignore[override]
        self._nav_sort = value; return self
    def show_in_nav(self, on: bool = True) -> "Page":  # type: ignore[override]
        self._show_in_nav = on; return self
    # Getters
    def get_slug(self) -> str: return self._slug
    def get_title(self) -> str: return self._title
    def get_nav_icon(self) -> str: return self._nav_icon
    def get_nav_sort(self) -> int: return self._nav_sort
    def is_shown_in_nav(self) -> bool: return self._show_in_nav
    def __repr__(self) -> str:
        return f"{type(self).__name__}(slug={self.get_slug()!r})"
class ListPage(Page):
    """Built-in resource list page (table + search + pagination)."""
    show_in_nav = False
class CreatePage(Page):
    """Built-in resource create page (form)."""
    show_in_nav = False
class EditPage(Page):
    """Built-in resource edit page (form pre-populated)."""
    show_in_nav = False
class ViewPage(Page):
    """Built-in resource view/detail page (infolist or auto-derived)."""
    show_in_nav = False
