from __future__ import annotations

from typing import Any, TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

if TYPE_CHECKING:
    from .panel import AdminPanel


class Page:
    """
    Base class for custom non-resource-backed admin pages.

    Subclass this to build arbitrary pages inside the admin panel —
    dashboards, reports, settings screens, multi-step wizards, etc.
    Each page appears as a nav entry in the sidebar under "Pages".

    Quick-start example::

        from nuru import Page
        from nuru.fields import Text, Section
        from nuru.columns import Text as TCol

        class ReportPage(Page):
            label = "Sales Report"
            slug  = "sales-report"
            icon  = "M9 19v-6a2 2 0 00-2-2H5a2 2 0 ..."  # SVG path d=

            # Every page must implement get_context().
            async def get_context(self, request: Request) -> dict:
                rows = await db.fetch_sales()
                return {
                    # ── pre-built nuru widgets ─────────────────────
                    # Use these keys to render standard nuru UI pieces
                    # inside your template with partials/form_grid.html,
                    # partials/detail_grid.html, or partials/table.html.
                    "sales": rows,
                    "total": sum(r["amount"] for r in rows),
                }

        panel.register_page(ReportPage)

    Then create a template at a path relative to your template dirs, e.g.
    ``templates/pages/sales_report.html``::

        {% extends "layout.html" %}

        {% block page_heading %}<h1>Sales Report</h1>{% endblock %}

        {% block content %}
          {# Render a detail grid using nuru fields #}
          {% set _fields = [Text(key="total")] %}
          {% set _form_cols = 1 %}
          {% set record = {"total": total | string} %}
          {% include "partials/form_grid.html" %}
        {% endblock %}

    Available template variables in addition to your get_context() return:
        panel_title, panel_prefix, current_user, current_path, resources,
        pages, brand_color, auth_enabled, htmx_local
    """

    # ── Override in subclasses ──────────────────────────────────────────
    label: str = ""
    label_plural: str = ""
    slug: str = ""
    icon: str = ""            # SVG path d="…" string; defaults to document icon
    template: str = ""        # Template path relative to template dirs; defaults to pages/<slug>.html

    # ── Internal ───────────────────────────────────────────────────────

    def __init__(self, *, panel: AdminPanel) -> None:
        self.panel = panel
        if not self.slug and self.label:
            self.slug = self.label.lower().replace(" ", "-")

    # ── Override this ──────────────────────────────────────────────────

    async def get_context(self, request: Request) -> dict:
        """Return a dict of template variables for this page.

        Called on every GET request for the page. Must be overridden.
        """
        return {}

    # ── Internals — do not override ────────────────────────────────────

    def _template_name(self) -> str:
        if self.template:
            return self.template
        safe_slug = self.slug.replace("-", "_")
        return f"pages/{safe_slug}.html"

    def _register_routes(self, router: APIRouter) -> None:
        page = self
        panel = self.panel

        @router.get(
            f"/{page.slug}",
            response_class=HTMLResponse,
            response_model=None,
            include_in_schema=False,
        )
        async def page_view(request: Request) -> HTMLResponse:
            if (redir := await panel._require_login(request)):
                return redir  # type: ignore[return-value]
            user = await panel._current_user(request)
            ctx = await page.get_context(request)
            html = panel._render(
                page._template_name(),
                ctx,
                user=user,
                request=request,
            )
            return HTMLResponse(html)
