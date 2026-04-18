from __future__ import annotations

from typing import Any, TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from .icons import resolve_icon

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
        from nuru.forms import Text, Section
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
        pages, palette_css, auth_enabled, htmx_local
    """

    # ── Override in subclasses ──────────────────────────────────────────
    label: str = ""
    label_plural: str = ""
    slug: str = ""
    icon: str = ""            # SVG path d="…" string; defaults to document icon
    template: str = ""        # Template path relative to template dirs; defaults to pages/<slug>.html
    show_in_nav: bool = True
    nav_label: str = ""
    nav_icon: str = ""
    nav_sort: int = 100

    # ── Internal ───────────────────────────────────────────────────────

    def __init__(self, *, panel: AdminPanel) -> None:
        self.panel = panel
        # Auto-generate slug from label only when the class hasn't explicitly
        # declared a slug (even an empty string, which means "root route /").
        if "slug" not in type(self).__dict__ and self.label:
            self.slug = self.label.lower().replace(" ", "-")

    # ── Override this ──────────────────────────────────────────────────

    async def get_context(self, request: Request) -> dict:
        """Return a dict of template variables for this page.

        Called on every GET request for the page. Must be overridden.
        """
        return {}

    async def handle_post(self, request: Request) -> Response:
        """Handle a POST submission to this page's URL.

        Override this to process form submissions from ``partials/form_widget.html``
        (or any other form that POSTs to this page's slug).

        The default implementation simply redirects back to the GET view.
        A POST route is only registered if this method is overridden in a
        subclass.

        Typical pattern::

            async def handle_post(self, request: Request) -> Response:
                form   = await request.form()
                title  = str(form.get("title", "")).strip()
                if not title:
                    # redirect back with an error flag
                    return RedirectResponse(
                        f"{self.panel.prefix}/{self.slug}?error=missing_title",
                        status_code=303,
                    )
                # ... do something with the data ...
                return RedirectResponse(
                    f"{self.panel.prefix}/{self.slug}?success=1",
                    status_code=303,
                )
        """
        return RedirectResponse(
            f"{self.panel.prefix}/{self.slug}", status_code=303
        )

    # ── Internals — do not override ────────────────────────────────────

    def _template_name(self) -> str:
        if self.template:
            return self.template
        safe_slug = self.slug.replace("-", "_")
        return f"pages/{safe_slug}.html"

    def _register_routes(self, router: APIRouter) -> None:
        page = self
        panel = self.panel
        # Empty slug → root route ("/"), otherwise "/{slug}"
        route_path = "/" if not page.slug else f"/{page.slug}"

        @router.get(
            route_path,
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

        # Only register a POST route if the subclass overrides handle_post.
        if type(page).handle_post is not Page.handle_post:

            @router.post(
                route_path,
                response_model=None,
                include_in_schema=False,
            )
            async def page_post(request: Request) -> Response:
                if (redir := await panel._require_login(request)):
                    return redir  # type: ignore[return-value]
                return await page.handle_post(request)


# ---------------------------------------------------------------------------
# Built-in pages — automatically registered unless overridden
# ---------------------------------------------------------------------------


class DashboardPage(Page):
    """
    Built-in dashboard page (route: ``/``).

    Override ``get_context`` or the full class to customise the dashboard.
    Provide a template at ``templates/dashboard.html`` in your own template
    dirs to replace the default layout entirely::

        class MyDashboard(DashboardPage):
            async def get_context(self, request):
                return {"stats": await fetch_stats()}

        panel.register_page(MyDashboard)
    """

    label = "Dashboard"
    slug = ""           # maps to the root route "/"
    nav_icon = "home"
    nav_sort = 0
    template = "dashboard.html"

    async def get_context(self, request: Request) -> dict:
        return {"resources": self.panel._resources}


class ProfilePage(Page):
    """
    Built-in profile page (route: ``/profile``).

    Not shown in the nav — accessed from the user-menu dropdown.
    Override the class or provide ``templates/profile.html`` to customise.
    """

    label = "Profile"
    slug = "profile"
    show_in_nav = False
    template = "profile.html"

    async def get_context(self, request: Request) -> dict:
        return {}
