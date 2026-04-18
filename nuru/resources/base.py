"""nuru.resources.base — Resource base class."""
from __future__ import annotations
from typing import Any, Type
class Resource:
    """
    Base class for all Nuru resources.
    Subclass style::
        class AuthorResource(Resource):
            model = Author
            label = "Author"
            label_plural = "Authors"
            slug = "authors"
            nav_icon = "user"
            def form(self): return AuthorForm()
            def table(self): return AuthorTable()
            def infolist(self): return None  # auto-derived from form
    make() inline style::
        Resource.make(Author).label("Author").form(lambda: AuthorForm())
    """
    # Class attributes — override in subclasses
    model: Any = None
    label: str = ""
    label_plural: str = ""
    slug: str = ""
    nav_icon: str = ""
    nav_sort: int = 0
    def __init__(self) -> None:
        self._model = self.__class__.model
        self._label = self.__class__.label
        self._label_plural = self.__class__.label_plural
        self._slug = self.__class__.slug
        self._nav_icon = self.__class__.nav_icon
        self._nav_sort = self.__class__.nav_sort
        self._form_factory = None
        self._table_factory = None
        self._infolist_factory = None
    # ------------------------------------------------------------------ #
    # Factory                                                              #
    # ------------------------------------------------------------------ #
    @classmethod
    def make(cls, model: Any = None) -> "Resource":
        obj = cls()
        if model is not None:
            obj._model = model
            if not obj._label:
                obj._label = model.__name__
        return obj
    # ------------------------------------------------------------------ #
    # Override in subclasses — return Form / Table / Infolist instances   #
    # ------------------------------------------------------------------ #
    def form(self):
        if self._form_factory:
            return self._form_factory()
        from nuru.forms.base import Form
        return Form()
    def table(self):
        if self._table_factory:
            return self._table_factory()
        from nuru.tables.base import Table
        return Table()
    def infolist(self):
        if self._infolist_factory:
            return self._infolist_factory()
        return None  # fall back to auto-derived infolist in ViewPage
    # ------------------------------------------------------------------ #
    # Fluent setters                                                       #
    # ------------------------------------------------------------------ #
    def label(self, value: str) -> "Resource":          # type: ignore[override]
        self._label = value; return self
    def label_plural(self, value: str) -> "Resource":   # type: ignore[override]
        self._label_plural = value; return self
    def slug(self, value: str) -> "Resource":           # type: ignore[override]
        self._slug = value; return self
    def nav_icon(self, value: str) -> "Resource":       # type: ignore[override]
        self._nav_icon = value; return self
    def nav_sort(self, value: int) -> "Resource":       # type: ignore[override]
        self._nav_sort = value; return self
    def set_form(self, factory) -> "Resource":
        self._form_factory = factory; return self
    def set_table(self, factory) -> "Resource":
        self._table_factory = factory; return self
    def set_infolist(self, factory) -> "Resource":
        self._infolist_factory = factory; return self
    # ------------------------------------------------------------------ #
    # Getters                                                              #
    # ------------------------------------------------------------------ #
    def get_model(self): return self._model
    def get_label(self) -> str:
        return self._label or (self._model.__name__ if self._model else "")
    def get_label_plural(self) -> str:
        return self._label_plural or (self.get_label() + "s")
    def get_slug(self) -> str:
        if self._slug:
            return self._slug
        return self.get_label().lower().replace(" ", "-")
    def get_nav_icon(self) -> str: return self._nav_icon
    def get_nav_sort(self) -> int: return self._nav_sort
    def __repr__(self) -> str:
        return f"{type(self).__name__}(slug={self.get_slug()!r})"
