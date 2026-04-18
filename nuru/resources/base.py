"""nuru.resources.base — Resource base class (v0.4 API).
Inherits from the legacy nuru.resource.Resource so all routing,
CRUD, and template rendering machinery works without modification.
New API adds:
  - make() factory
  - form() / table() / infolist() methods (return Form / Table / Infolist)
  - _bridge_from_new_api() auto-populates legacy attributes from those methods
App authors subclass Resource and override form(), table(), infolist():
    class AuthorResource(Resource):
        model = Author
        label = "Author"
        def form(self):
            return AuthorForm()
        def table(self):
            return AuthorTable()
        def infolist(self):         # optional; falls back to auto-derived
            return AuthorInfolist()
"""
from __future__ import annotations
from typing import Any
class Resource:
    """New-style Resource base.  Inherits legacy routing after _bridge."""
    # Class attributes — override in subclasses (same as legacy)
    model: Any = None
    label: str = ""
    label_plural: str = ""
    slug: str = ""
    nav_icon: str = ""
    nav_sort: int = 100
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
    # ------------------------------------------------------------------ #
    # Factory                                                              #
    # ------------------------------------------------------------------ #
    @classmethod
    def make(cls, model: Any = None) -> "Resource":
        """Inline factory.  Returns a class (not instance) pre-configured."""
        # Dynamically create a subclass so make() can be used fluently:
        #   r = Resource.make(Author).with_label("Author")
        name = f"_Dynamic{cls.__name__}"
        bases = (cls,)
        attrs: dict = {}
        if model is not None:
            attrs["model"] = model
            attrs["label"] = model.__name__
        klass = type(name, bases, attrs)
        return klass
    # ------------------------------------------------------------------ #
    # Override in subclasses — return Form / Table / Infolist instances   #
    # ------------------------------------------------------------------ #
    def form(self):
        """Return a Form instance for create/edit pages."""
        from nuru.forms.base import Form
        return Form()
    def table(self):
        """Return a Table instance for the list page."""
        from nuru.tables.base import Table
        return Table()
    def infolist(self):
        """Return an Infolist instance for the view/detail page.
        Return None to auto-derive entries from the form's fields."""
        return None
    # ------------------------------------------------------------------ #
    # Bridge: populate legacy attributes from new API                     #
    # ------------------------------------------------------------------ #
    def _bridge_from_new_api(self) -> None:
        """Populate legacy form_fields / table_columns / detail_fields
        from form() / table() / infolist() if they are overridden and
        return non-empty results."""
        from nuru.forms.base import Form
        from nuru.tables.base import Table
        from nuru.infolists.base import Infolist
        # Form fields
        try:
            form_obj = self.form()
            if isinstance(form_obj, Form):
                fields = form_obj.fields()
                if fields:
                    self.form_fields = fields  # type: ignore[attr-defined]
        except Exception:
            pass
        # Table columns + row actions
        try:
            table_obj = self.table()
            if isinstance(table_obj, Table):
                cols = table_obj.columns()
                if cols:
                    self.table_columns = cols  # type: ignore[attr-defined]
                actions = table_obj.row_actions()
                if actions:
                    self.row_actions = actions  # type: ignore[attr-defined]
        except Exception:
            pass
        # Detail fields (from infolist entries)
        try:
            il = self.infolist()
            if isinstance(il, Infolist):
                entries = il.entries()
                if entries:
                    self.detail_fields = entries  # type: ignore[attr-defined]
        except Exception:
            pass
    def __repr__(self) -> str:
        return f"{type(self).__name__}(slug={getattr(self, 'slug', '')})"
