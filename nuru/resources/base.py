"""nuru.resources.base — Resource base class (v0.4 API).

App authors subclass Resource and override form(), table(), infolist()::

    class AuthorResource(Resource):
        model = Author
        label = "Author"
        session_factory = get_session

        def form(self) -> Form:
            return Form().schema([...])

        def table(self) -> Table:
            return Table().schema([...])

        def infolist(self) -> Infolist:   # optional; falls back to form fields
            return Infolist().schema([...])

The routing/CRUD machinery is inherited from nuru.resource.Resource (internal
engine).  _bridge_from_new_api() is called automatically in __init__ to
populate form_fields / table_columns / detail_fields from the methods above.
"""
from __future__ import annotations
from typing import Any

# The routing engine — kept as the internal implementation.
# Users should subclass nuru.resources.Resource (this class), not the engine directly.
from nuru.resource import Resource as _RoutingEngine


class Resource(_RoutingEngine):
    """New-style Resource base.  Subclass and override form() / table() / infolist()."""

    # ------------------------------------------------------------------ #
    # Factory                                                              #
    # ------------------------------------------------------------------ #
    @classmethod
    def make(cls, model: Any = None) -> "Resource":
        """Inline factory — creates a dynamic subclass pre-configured with *model*."""
        attrs: dict = {}
        if model is not None:
            attrs["model"] = model
            attrs["label"] = model.__name__
        return type(f"_Dynamic{cls.__name__}", (cls,), attrs)  # type: ignore[return-value]

    # ------------------------------------------------------------------ #
    # Override in subclasses — return Form / Table / Infolist instances   #
    # ------------------------------------------------------------------ #
    def form(self):
        """Return a Form instance for create/edit pages. Override in subclasses."""
        from nuru.forms.base import Form
        return Form()

    def table(self):
        """Return a Table instance for the list page. Override in subclasses."""
        from nuru.tables.base import Table
        return Table()

    def infolist(self):
        """Return an Infolist for the view/detail page, or None to auto-derive."""
        return None

    # ------------------------------------------------------------------ #
    # Bridge — called by _RoutingEngine.__init__ automatically            #
    # ------------------------------------------------------------------ #
    def _bridge_from_new_api(self) -> None:
        """Populate form_fields / table_columns / detail_fields from
        form() / table() / infolist() overrides."""
        from nuru.forms.base import Form
        from nuru.tables.base import Table
        from nuru.infolists.base import Infolist

        try:
            form_obj = self.form()
            if isinstance(form_obj, Form):
                fields = form_obj.fields()
                if fields:
                    self.form_fields = fields
                actions = form_obj.actions()
                if actions:
                    self.form_actions = actions
        except Exception:
            pass

        try:
            table_obj = self.table()
            if isinstance(table_obj, Table):
                cols = table_obj.columns()
                if cols:
                    self.table_columns = cols
                actions = table_obj.row_actions()
                if actions:
                    self.row_actions = actions
        except Exception:
            pass

        try:
            il = self.infolist()
            if isinstance(il, Infolist):
                entries = il.entries()
                if entries:
                    self.detail_fields = entries
        except Exception:
            pass

    def __repr__(self) -> str:
        return f"{type(self).__name__}(slug={getattr(self, 'slug', '')})"
