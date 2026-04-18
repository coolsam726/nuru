"""nuru.pages.base — Page base class and built-in page types."""
from __future__ import annotations
from typing import Any
from nuru.page import Page as _LegacyPage


class Page(_LegacyPage):
    """
    Base class for all Nuru pages (custom and built-in).
    Subclasses get full legacy routing (get_context, handle_post, self.panel)
    plus the new fluent make() API.
    """
    slug: str = ""
    title: str = ""
    nav_icon: str = ""
    nav_sort: int = 100   # after resource nav items
    show_in_nav: bool = True

    def __init__(self, *, panel=None) -> None:  # type: ignore[override]
        if panel is not None:
            super().__init__(panel=panel)
        # panel may be injected later by the legacy registration machinery

    @classmethod
    def make(cls) -> "Page":
        # Instantiate without panel for use outside of the routing engine
        instance = cls.__new__(cls)
        instance.slug = cls.slug
        instance.nav_icon = cls.nav_icon
        instance.nav_sort = cls.nav_sort
        instance.show_in_nav = cls.show_in_nav
        return instance

    # Override in subclasses
    async def content(self, request: Any) -> dict:
        return {}

    def __repr__(self) -> str:
        return f"{type(self).__name__}(slug={self.slug!r})"


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
