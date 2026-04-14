from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

if TYPE_CHECKING:
    from .auth import AuthBackend
    from .resource import Resource

_PACKAGE_DIR = Path(__file__).parent
_TEMPLATES_DIR = _PACKAGE_DIR / "templates"
_STATIC_DIR = _PACKAGE_DIR / "static"
_HTMX_LOCAL = (_STATIC_DIR / "htmx.min.js").exists()


def _field_value(record: Any, key: str) -> Any:
    """
    Jinja2 filter: extract a field value from either a dict or an ORM object.
    Usage in templates: {{ record | field_value('email') }}
    """
    if record is None:
        return ""
    if isinstance(record, dict):
        return record.get(key, "")
    return getattr(record, key, "")


class AdminPanel:
    """
    The top-level object that wires together resources, dashboards,
    auth, and navigation, then mounts everything onto a FastAPI app.

    Multiple panels can coexist on the same FastAPI app as long as
    each has a distinct prefix::

        staff_panel = AdminPanel(title="Staff Portal", prefix="/staff")
        ops_panel   = AdminPanel(title="Ops",          prefix="/ops")

        staff_panel.register(UserResource)
        ops_panel.register(ServerResource)

        staff_panel.mount(app)
        ops_panel.mount(app)

    Each panel gets its own navigation, branding, and route namespace.
    Static files are shared from the same package directory but mounted
    under each panel's own prefix so URLs never collide.
    """

    def __init__(
        self,
        *,
        title: str = "Admin",
        prefix: str = "/admin",
        brand_color: str = "#6366f1",
        logo_url: str | None = None,
        per_page: int = 25,
        auth: AuthBackend | None = None,
    ) -> None:
        self.title = title
        self.prefix = prefix.rstrip("/")
        self.brand_color = brand_color
        self.logo_url = logo_url
        self.per_page = per_page
        self.auth = auth

        # Derive a safe identifier from the prefix for naming purposes.
        # "/admin" → "admin", "/staff/panel" → "staff_panel"
        self._panel_id = self.prefix.strip("/").replace("/", "_") or "admin"

        self._resources: list[type[Resource]] = []
        self._router = APIRouter(prefix=self.prefix)
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=select_autoescape(["html"]),
        )
        self._jinja_env.globals.update(self._template_globals())
        self._jinja_env.filters["field_value"] = _field_value

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, resource_cls: type[Resource]) -> None:
        """Register a Resource class with this panel."""
        self._resources.append(resource_cls)

    def mount(self, app: FastAPI) -> None:
        """
        Attach all admin routes and static files to an existing FastAPI app.

        Safe to call multiple times on the same app with different panels —
        each panel uses a unique mount name derived from its prefix so
        there are no collisions.
        """
        self._build_routes()
        self._mount_static(app)
        app.include_router(self._router)

    # ------------------------------------------------------------------
    # Route builders
    # ------------------------------------------------------------------

    def _build_routes(self) -> None:
        if self.auth is not None:
            self._add_login_routes()
        self._add_dashboard_route()
        for resource_cls in self._resources:
            resource = resource_cls(panel=self)
            resource._register_routes(self._router)

    def _add_login_routes(self) -> None:
        """Add GET /login, POST /login, and GET /logout routes."""
        panel = self

        @self._router.get("/login", response_class=HTMLResponse, response_model=None, include_in_schema=False)
        async def login_page(
            request: Request,
            next: str | None = None,
        ) -> HTMLResponse | RedirectResponse:
            # Already logged in → go straight to the panel.
            user = await panel.auth.get_current_user(request)  # type: ignore[union-attr]
            if user is not None:
                return RedirectResponse(f"{panel.prefix}/", status_code=303)
            html = panel._render("login.html", {"error": None, "next": next})
            return HTMLResponse(html)

        @self._router.post("/login", response_class=HTMLResponse, response_model=None, include_in_schema=False)
        async def login_submit(
            request: Request,
            next: str | None = None,
        ) -> HTMLResponse | RedirectResponse:
            form  = await request.form()
            username = str(form.get("username", ""))
            password = str(form.get("password", ""))

            ok = await panel.auth.authenticate(username, password)  # type: ignore[union-attr]
            if not ok:
                html = panel._render(
                    "login.html",
                    {"error": "Invalid username or password.", "next": next},
                )
                return HTMLResponse(html, status_code=401)

            # Determine safe redirect target (must stay on same panel).
            destination = next or f"{panel.prefix}/"
            if not destination.startswith(panel.prefix):
                destination = f"{panel.prefix}/"

            response: Response = RedirectResponse(destination, status_code=303)
            panel.auth.set_session(response, username)  # type: ignore[union-attr]
            return response  # type: ignore[return-value]

        @self._router.get("/logout", include_in_schema=False)
        async def logout() -> RedirectResponse:
            response: Response = RedirectResponse(
                f"{panel.prefix}/login", status_code=303
            )
            panel.auth.clear_session(response)  # type: ignore[union-attr]
            return response  # type: ignore[return-value]

    def _add_dashboard_route(self) -> None:
        panel = self

        @self._router.get("/", response_class=HTMLResponse, response_model=None, include_in_schema=False)
        async def dashboard(request: Request) -> HTMLResponse | RedirectResponse:
            if (redir := await panel._require_login(request)):
                return redir
            user = await panel._current_user(request)
            html = panel._render("dashboard.html", {
                "resources": panel._resources,
            }, user=user, request=request)
            return HTMLResponse(html)

    def _mount_static(self, app: FastAPI) -> None:
        """
        Mount the package static directory under this panel's prefix.

        Each panel gets its own mount name (e.g. "adminpanel_static_admin",
        "adminpanel_static_staff") so multiple panels on the same app
        never conflict.
        """
        if not (_STATIC_DIR.exists() and any(_STATIC_DIR.iterdir())):
            return

        mount_name = f"adminpanel_static_{self._panel_id}"
        mount_path = f"{self.prefix}/static"

        # Guard against accidentally mounting the same panel twice
        existing_names = {r.name for r in app.routes if hasattr(r, "name")}
        if mount_name in existing_names:
            return

        app.mount(
            mount_path,
            StaticFiles(directory=str(_STATIC_DIR)),
            name=mount_name,
        )

    # ------------------------------------------------------------------
    # Templating helpers
    # ------------------------------------------------------------------

    async def _require_login(self, request: Request) -> RedirectResponse | None:
        """Return a redirect to the login page if the request is not authenticated."""
        if self.auth is None:
            return None
        user = await self.auth.get_current_user(request)
        if user is None:
            next_url = str(request.url)
            return RedirectResponse(
                f"{self.prefix}/login?next={next_url}", status_code=303
            )
        return None

    async def _current_user(self, request: Request) -> Any | None:
        """Return the current user, or None if auth is disabled."""
        if self.auth is None:
            return None
        return await self.auth.get_current_user(request)

    def _render(self, template_name: str, context: dict, *, user: Any = None, request: Request | None = None) -> str:
        template = self._jinja_env.get_template(template_name)
        current_path = str(request.url.path) if request is not None else ""
        return template.render(current_user=user, current_path=current_path, **context)

    def _template_globals(self) -> dict:
        """Values injected into every template automatically."""
        return {
            "panel_title":  self.title,
            "panel_prefix": self.prefix,
            "brand_color":  self.brand_color,
            "logo_url":     self.logo_url,
            "htmx_local":   _HTMX_LOCAL,
            "per_page":     self.per_page,
            "resources":    self._resources,
            "auth_enabled": self.auth is not None,
            "current_user": None,   # overridden per-request via _render(user=...)
        }
