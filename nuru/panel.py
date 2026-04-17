from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles
from jinja2 import ChoiceLoader, Environment, FileSystemLoader, select_autoescape
from .icons import render_icon, resolve_icon
from .palette import palette_css_vars

if TYPE_CHECKING:
    from .auth import AuthBackend
    from .page import Page
    from .resource import Resource

_PACKAGE_DIR = Path(__file__).parent
_TEMPLATES_DIR = _PACKAGE_DIR / "templates"
_STATIC_DIR = _PACKAGE_DIR / "static"
_HTMX_LOCAL = (_STATIC_DIR / "htmx.min.js").exists()
_DEFAULT_RESOURCE_NAV_ICON = "M4 6h16M4 10h16M4 14h16M4 18h16"
_DEFAULT_PAGE_NAV_ICON = "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"


@dataclass(frozen=True)
class _NavItem:
    label: str
    href: str
    icon: str
    sort: int


def _field_value(record: Any, key: str) -> Any:
    """
    Jinja2 filter: extract a field value from either a dict or an ORM object.
    Supports dot-notation traversal, e.g. 'author.name'.
    Usage in templates: {{ record | field_value('author.name') }}
    """
    obj = record
    for part in key.split("."):
        if obj is None:
            return ""
        if isinstance(obj, dict):
            obj = obj.get(part, "")
        else:
            obj = getattr(obj, part, "")
    return obj


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
        primary: str | None = None,
        secondary: str | None = None,
        accent: str | None = None,
        info: str | None = None,
        success: str | None = None,
        danger: str | None = None,
        warning: str | None = None,
        logo_url: str | None = None,
        per_page: int = 25,
        auth: "AuthBackend | None" = None,
        permission_checker: Any | None = None,
        template_dirs: list[str | Path] | None = None,
        extra_css: list[str] | str | None = None,
        extra_js: list[str] | str | None = None,
        upload_dir: "Path | str | None" = None,
        upload_backend: Any | None = None,
    ) -> None:
        self.title = title
        self.prefix = prefix.rstrip("/")
        self.primary   = primary
        self.secondary = secondary
        self.accent    = accent
        self.info      = info
        self.success   = success
        self.danger    = danger
        self.warning   = warning
        self.logo_url = logo_url
        self.per_page = per_page
        self.auth = auth
        # Permission checker: callable(user, action, resource) -> bool
        # Default to nuru.auth.default_permission_checker if not supplied.
        from . import auth as _auth
        self.permission_checker = permission_checker or _auth.default_permission_checker
        if extra_css is None:
            self.extra_css: list[str] = []
        elif isinstance(extra_css, str):
            self.extra_css = [extra_css]
        else:
            self.extra_css = list(extra_css)
        if extra_js is None:
            self.extra_js: list[str] = []
        elif isinstance(extra_js, str):
            self.extra_js = [extra_js]
        else:
            self.extra_js = list(extra_js)

        # -- File upload --
        if upload_backend is not None:
            self.upload_backend = upload_backend
        else:
            from .storage.local import LocalFileBackend as _LocalFB
            _udir = Path(upload_dir) if upload_dir else Path.cwd() / "uploads"
            self.upload_backend = _LocalFB(_udir)
        # Expose the upload dir for static serving
        self.upload_dir: Path = self.upload_backend.upload_dir

        # Derive a safe identifier from the prefix for naming purposes.
        # "/admin" → "admin", "/staff/panel" → "staff_panel"
        self._panel_id = self.prefix.strip("/").replace("/", "_") or "admin"

        self._resources: list[type[Resource]] = []
        self._pages: list[type[Page]] = []
        self._nav_items: list[_NavItem] = []
        self._router = APIRouter(prefix=self.prefix)

        # Build loader: user dirs (highest priority) → built-in package templates
        loaders: list[FileSystemLoader] = []
        for d in (template_dirs or []):
            loaders.append(FileSystemLoader(str(d)))
        loaders.append(FileSystemLoader(str(_TEMPLATES_DIR)))

        self._jinja_env = Environment(
            loader=ChoiceLoader(loaders),
            autoescape=select_autoescape(["html"]),
        )
        self._jinja_env.globals.update(self._template_globals())
        self._jinja_env.filters["field_value"] = _field_value

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_extra_js(self, url: str) -> None:
        """Append a JS URL to load on every panel page (idempotent)."""
        if url not in self.extra_js:
            self.extra_js.append(url)
            self._jinja_env.globals["extra_js"] = list(self.extra_js)

    def add_template_dir(self, path: "str | Path") -> None:
        """Prepend a template directory so its partials take priority."""
        from jinja2 import ChoiceLoader
        existing = self._jinja_env.loader
        new_loader = FileSystemLoader(str(path))
        if isinstance(existing, ChoiceLoader):
            loaders = [new_loader] + list(existing.loaders)
        else:
            loaders = [new_loader, existing]
        self._jinja_env.loader = ChoiceLoader(loaders)

    def register(self, resource_cls: type[Resource]) -> None:
        """Register a Resource class with this panel."""
        self._resources.append(resource_cls)

    def register_page(self, page_cls: type[Page]) -> None:
        """Register a Page class with this panel."""
        self._pages.append(page_cls)

    def register_nav_item(self, *, label: str, href: str, icon: str = "", sort: int = 100) -> None:
        """Register a custom sidebar item that is not tied to a resource or page."""
        self._nav_items.append(_NavItem(label=label, href=href, icon=icon, sort=sort))

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
        from .page import DashboardPage, ProfilePage
        if self.auth is not None:
            self._add_login_routes()

        # Build the model registry: maps model class name → (model_cls, session_factory).
        # Only models wired to a registered Resource are allowed through the search
        # endpoint — this prevents arbitrary model enumeration.
        self._model_registry: dict[str, tuple] = {}
        for resource_cls in self._resources:
            m = getattr(resource_cls, "model", None)
            sf = getattr(resource_cls, "session_factory", None)
            if m is not None and sf is not None:
                self._model_registry[m.__name__] = (m, sf)

        # ── GET /_model_search — generic JSON search for model-based Select fields ──
        # Queried directly by the combobox template; resolves options from the model
        # layer without requiring a matching Resource.
        self._add_model_search_route()

        # ── File upload endpoint ──
        self._add_upload_routes()

        # Register built-in pages unless the user has overridden them
        registered_slugs = {cls.slug for cls in self._pages}
        if "" not in registered_slugs:
            DashboardPage(panel=self)._register_routes(self._router)
        if "profile" not in registered_slugs:
            ProfilePage(panel=self)._register_routes(self._router)
        for resource_cls in self._resources:
            resource = resource_cls(panel=self)
            resource._register_routes(self._router)
        for page_cls in self._pages:
            page = page_cls(panel=self)
            page._register_routes(self._router)

    def _nav_entries(self, has_perm: Any = None) -> list[dict[str, Any]]:
        from .page import DashboardPage, ProfilePage
        items: list[_NavItem] = list(self._nav_items)

        # Include built-in pages (in nav order) unless the user has overridden them
        registered_slugs = {cls.slug for cls in self._pages}
        builtin_page_cls: list[type] = []
        if "" not in registered_slugs:
            builtin_page_cls.append(DashboardPage)
        if "profile" not in registered_slugs:
            builtin_page_cls.append(ProfilePage)

        for resource_cls in self._resources:
            if not getattr(resource_cls, "show_in_nav", True):
                continue
            slug = resource_cls.slug if resource_cls.slug else resource_cls.label.lower().replace(" ", "-")
            # Filter: skip resources the current user cannot list.
            if has_perm is not None and not has_perm(f"{slug}:list"):
                continue
            label = resource_cls.nav_label or (resource_cls.label_plural if resource_cls.label_plural else resource_cls.label + "s")
            icon_name = resource_cls.nav_icon or "folder"
            icon = resolve_icon(icon_name)
            items.append(_NavItem(label=label, href=f"{self.prefix}/{slug}", icon=icon, sort=getattr(resource_cls, "nav_sort", 100)))

        for page_cls in builtin_page_cls + self._pages:
            if not getattr(page_cls, "show_in_nav", True):
                continue
            slug = page_cls.slug
            href = f"{self.prefix}/" if not slug else f"{self.prefix}/{slug}"
            label = page_cls.nav_label or page_cls.label
            icon_name = page_cls.nav_icon or getattr(page_cls, "icon", "") or "document"
            icon = resolve_icon(icon_name)
            items.append(_NavItem(label=label, href=href, icon=icon, sort=getattr(page_cls, "nav_sort", 100)))

        items.sort(key=lambda item: (item.sort, item.label.lower(), item.href))
        return [item.__dict__ for item in items]

    def _add_model_search_route(self) -> None:
        """Register GET /_model_search — the portable combobox search endpoint.

        The ``Select(model=MyModel)`` field template calls this endpoint to
        populate its dropdown.  Only models that are attached to a registered
        Resource are accessible, preventing enumeration of arbitrary models.

        Query params:
            model       — exact class name of the SQLModel (e.g. ``"Author"``)
            q           — optional search string (ilike on label_field)
            value_field — attr to use as the option value  (default: PK)
            label_field — attr to use as the option label  (default: str())
            per_page    — max rows returned                 (default: 200)
        """
        panel = self
        from fastapi.responses import JSONResponse as _JSONResponse

        @self._router.get("/_model_search", response_model=None, include_in_schema=False)
        async def model_search_endpoint(
            request: Request,
            model: str,
            q: str | None = None,
            value_field: str = "",
            label_field: str = "",
            per_page: int = 200,
        ) -> _JSONResponse:
            if await panel._require_login(request):
                return _JSONResponse([], status_code=401)

            entry = panel._model_registry.get(model)
            if entry is None:
                # Model not registered — refuse silently to avoid leaking schema.
                return _JSONResponse([])

            model_cls, session_factory = entry

            # Require that the caller has list permission for the Resource
            # that exposes this model. This prevents unauthorised users from
            # enumerating model options via the search endpoint.
            try:
                # Find the Resource class that is wired to this model.
                resource_slug = None
                for resource_cls in panel._resources:
                    if getattr(resource_cls, "model", None) is model_cls:
                        resource_slug = getattr(resource_cls, "slug", None) or resource_cls.__name__.lower()
                        break

                checker = getattr(panel, "permission_checker", None)
                if panel.auth is not None and checker is not None:
                    user = await panel._current_user(request)
                    # permission_checker may be sync or async
                    res = checker(user, f"{resource_slug}:list", None) if resource_slug else False
                    import inspect
                    if inspect.isawaitable(res):
                        res = await res
                    if not res:
                        return _JSONResponse([])
            except Exception:
                # On any error during permission checking, refuse silently.
                return _JSONResponse([])

            # Resolve the primary key column name.
            try:
                pk_cols = list(model_cls.__table__.primary_key.columns)
                pk_name = pk_cols[0].key if pk_cols else "id"
            except AttributeError:
                pk_name = "id"

            vf = value_field or pk_name
            lf = label_field or ""

            try:
                from sqlalchemy import or_
                from sqlmodel import select as _select

                async with session_factory() as session:
                    query = _select(model_cls)
                    if q and lf and hasattr(model_cls, lf):
                        query = query.where(
                            getattr(model_cls, lf).ilike(f"%{q}%")
                        )
                    query = query.limit(per_page)
                    records = (await session.exec(query)).all()

                out: list[dict] = []
                for rec in records:
                    v = getattr(rec, vf, None)
                    # Determine a sensible label. If a label_field was
                    # requested but its value is empty/None, fall back to
                    # `str(rec)` or the value field so the combobox doesn't
                    # render blank options.
                    if lf and hasattr(rec, lf):
                        candidate = getattr(rec, lf, None)
                        if candidate is None or (isinstance(candidate, str) and candidate.strip() == ""):
                            candidate = str(rec)
                            if not candidate:
                                candidate = str(v) if v is not None else ""
                        lbl = str(candidate)
                    else:
                        lbl = str(rec)
                        if lbl is None or lbl == "":
                            lbl = str(v) if v is not None else ""

                    out.append({
                        "value": str(v)   if v   is not None else "",
                        "label": lbl,
                    })
                return _JSONResponse(out)
            except Exception:
                return _JSONResponse([])

    def _add_upload_routes(self) -> None:
        """Register POST and DELETE /_upload for FilePond file uploads.

        POST /_upload
            Accepts a multipart file named ``file`` (or any name FilePond uses).
            Query param ``directory`` specifies the sub-directory under the
            upload root.
            Returns a plain-text response with the server ID (relative path).

        DELETE /_upload
            Body should be the server ID returned by the POST.
            Deletes the file from storage and returns 204.

        GET /_upload/restore?id=<server_id>
            Return the file so FilePond can show a preview for existing values.

        GET /_upload/load?source=<server_id>
            Alias for restore (FilePond uses either depending on config).
        """
        from fastapi import File, UploadFile
        from fastapi.responses import Response as _Resp, PlainTextResponse, StreamingResponse
        import mimetypes as _mt

        panel = self

        @self._router.post("/_upload", response_model=None, include_in_schema=False)
        async def upload_file(
            request: Request,
            directory: str = "",
        ) -> PlainTextResponse:
            if await panel._require_login(request):
                return PlainTextResponse("Unauthorized", status_code=401)

            form = await request.form()
            # FilePond sends the file under the field name configured in its
            # `name` option — default is "file".  Fall back to first file found.
            uploaded = None
            for key, val in form.items():
                if hasattr(val, "filename"):
                    uploaded = val
                    break

            if uploaded is None:
                return PlainTextResponse("No file", status_code=400)

            content = await uploaded.read()

            class _Buf:
                """Minimal file-like wrapper around bytes for LocalFileBackend."""
                def __init__(self, data: bytes) -> None:
                    self._data = data
                def read(self) -> bytes:
                    return self._data

            meta = panel.upload_backend.save(
                _Buf(content),
                original_filename=uploaded.filename or "upload",
                directory=directory,
                content_type=uploaded.content_type,
            )
            return PlainTextResponse(meta["server_id"], status_code=200)

        @self._router.delete("/_upload", response_model=None, include_in_schema=False)
        async def revert_upload(request: Request) -> _Resp:
            if await panel._require_login(request):
                return _Resp(status_code=401)
            body = await request.body()
            server_id = body.decode().strip()
            panel.upload_backend.delete(server_id)
            return _Resp(status_code=204)

        @self._router.get("/_upload/restore", response_model=None, include_in_schema=False)
        async def restore_file(request: Request, id: str) -> _Resp:
            if await panel._require_login(request):
                return _Resp(status_code=401)
            path = panel.upload_backend.path(id)
            if path is None:
                return _Resp(status_code=404)
            ct = _mt.guess_type(str(path))[0] or "application/octet-stream"
            data = path.read_bytes()
            headers = {
                "Content-Disposition": f'inline; filename="{path.name}"',
                "Content-Length": str(len(data)),
            }

            def _iter():
                yield data

            return StreamingResponse(_iter(), media_type=ct, headers=headers)

        @self._router.get("/_upload/load", response_model=None, include_in_schema=False)
        async def load_file(request: Request, source: str) -> _Resp:
            return await restore_file(request, id=source)

    def _add_login_routes(self) -> None:
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
            # Allow the backend to store its preferred identifier (e.g. user PK
            # for DatabaseAuthBackend, or username for SimpleAuthBackend).
            session_id = await panel.auth.get_session_user_id(username)  # type: ignore[union-attr]
            panel.auth.set_session(response, session_id)  # type: ignore[union-attr]
            return response  # type: ignore[return-value]

        @self._router.get("/logout", include_in_schema=False)
        async def logout() -> RedirectResponse:
            response: Response = RedirectResponse(
                f"{panel.prefix}/login", status_code=303
            )
            panel.auth.clear_session(response)  # type: ignore[union-attr]
            return response  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Permission sync
    # ------------------------------------------------------------------

    async def sync_permissions(self, session_factory: Any) -> None:
        """Upsert ``nuru_permission`` rows for every registered resource.

        Call this at application startup alongside ``sync_schema``::

            from nuru.migrations import sync_schema

            await sync_schema(engine, SQLModel.metadata)
            await panel.sync_permissions(get_session)

        The method creates one permission row per ``{slug}:{action}`` pair for
        each registered resource, using the STANDARD_ACTIONS list from
        :mod:`nuru.roles` (``list``, ``view``, ``create``, ``edit``,
        ``delete``, ``action``).  Rows are inserted only when they do not
        already exist so the call is safe to repeat on every restart.
        """
        from sqlmodel import select
        from .roles import STANDARD_ACTIONS, Permission

        slugs: list[str] = []
        for resource_cls in self._resources:
            slug = resource_cls.slug if resource_cls.slug else resource_cls.label.lower().replace(" ", "-")
            slugs.append(slug)

        # Build the full set of codenames that should exist.
        desired: list[tuple[str, str]] = [
            (f"{slug}:{action}", f"{resource_cls.label_plural or resource_cls.label} — {action}")
            for resource_cls, slug in zip(self._resources, slugs)
            for action in STANDARD_ACTIONS
        ]
        # Always include the superuser wildcard.
        desired.append(("*", "Superuser — all permissions"))

        async with session_factory() as session:
            existing = set(
                (await session.exec(select(Permission.codename))).all()
            )
            new_perms = [
                Permission(codename=codename, label=label)
                for codename, label in desired
                if codename not in existing
            ]
            if new_perms:
                session.add_all(new_perms)
                await session.commit()

    def _mount_static(self, app: FastAPI) -> None:
        """
        Mount the package static directory under this panel's prefix.

        Each panel gets its own mount name (e.g. "nuru_static_admin",
        "nuru_static_staff") so multiple panels on the same app
        never conflict.
        """
        if not (_STATIC_DIR.exists() and any(_STATIC_DIR.iterdir())):
            return

        mount_name = f"nuru_static_{self._panel_id}"
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

        # Mount uploads directory so uploaded files can be served statically.
        uploads_mount_name = f"nuru_uploads_{self._panel_id}"
        uploads_mount_path = f"{self.prefix}/uploads"
        if uploads_mount_name not in existing_names:
            # Ensure uploads dir exists before mounting
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            app.mount(
                uploads_mount_path,
                StaticFiles(directory=str(self.upload_dir)),
                name=uploads_mount_name,
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

    async def _render_error(
        self,
        status_code: int,
        title: str,
        message: str,
        *,
        request: Request | None = None,
    ) -> "HTMLResponse":
        """Render a styled error page and return an HTMLResponse with *status_code*."""
        from fastapi.responses import HTMLResponse

        user = None
        if request is not None:
            try:
                user = await self._current_user(request)
            except Exception:
                pass
        html = self._render(
            "error.html",
            {"error_code": status_code, "error_title": title, "error_message": message},
            user=user,
            request=request,
        )
        return HTMLResponse(html, status_code=status_code)

    def _render(self, template_name: str, context: dict, *, user: Any = None, request: Request | None = None) -> str:
        template = self._jinja_env.get_template(template_name)
        current_path = str(request.url.path) if request is not None else ""

        # Build a synchronous has_perm helper that templates can call directly.
        # The permission checker must be synchronous (async checkers are handled
        # at the route level via _user_allowed).  When auth is disabled, or no
        # checker is configured, everything is visible.
        checker = getattr(self, "permission_checker", None)
        if self.auth is None or checker is None:
            def has_perm(codename: str) -> bool:
                return True
        else:
            def has_perm(codename: str) -> bool:  # type: ignore[misc]
                try:
                    return bool(checker(user, codename, None))
                except Exception:
                    return False

        # If any fields expose `options` as a callable, invoke them at
        # render-time so templates receive a concrete list. We do this
        # temporarily (mutate -> render -> restore) to avoid permanently
        # altering the Resource definition object.
        import inspect

        originals: list[tuple[object, object]] = []
        resource = context.get("resource")
        record = context.get("record")
        try:
            if resource is not None and hasattr(resource, "_flat_form_fields"):
                for field in resource._flat_form_fields:
                    getter = getattr(field, "get_options", None)
                    if getter is None:
                        continue
                    opts = getter()
                    if callable(opts):
                        try:
                            sig = inspect.signature(opts)
                            # prefer calling with the current record if the
                            # callable accepts a parameter
                            if len(sig.parameters) == 0:
                                new_opts = opts()
                            else:
                                new_opts = opts(record)
                        except Exception:
                            # on any error, skip resolving this callable
                            continue
                        # skip awaitables (we don't run async callables here)
                        if hasattr(new_opts, "__await__"):
                            continue
                        originals.append((field, opts))  # save original callable
                        field.options(new_opts)

            return template.render(
                current_user=user,
                current_path=current_path,
                nav_items=self._nav_entries(has_perm=has_perm),
                has_perm=has_perm,
                **context,
            )
        finally:
            # restore any mutated options
            for field, orig in originals:
                try:
                    field.options(orig)
                except Exception:
                    pass

    def _template_globals(self) -> dict:
        """Values injected into every template automatically."""
        # Only generate palette overrides for colors explicitly set by the caller.
        # Colors left as None fall back to the Tailwind @theme defaults.
        _overrides = {
            name: color
            for name, color in {
                "primary":   self.primary,
                "secondary": self.secondary,
                "accent":    self.accent,
                "info":      self.info,
                "success":   self.success,
                "danger":    self.danger,
                "warning":   self.warning,
            }.items()
            if color is not None
        }
        palette_css = "\n".join(
            palette_css_vars(name, color) for name, color in _overrides.items()
        )
        return {
            "render_icon":        render_icon,
            "panel_title":        self.title,
            "panel_prefix":       self.prefix,
            "palette_css":        palette_css,
            "logo_url":           self.logo_url,
            "htmx_local":         _HTMX_LOCAL,
            "per_page":           self.per_page,
            "resources":          self._resources,
            "pages":              self._pages,
            "auth_enabled":       self.auth is not None,
            "extra_css":          self.extra_css,
            "extra_js":           self.extra_js,
            "has_perm":            lambda codename: True,  # overridden per-request in _render()
            "current_user":        None,   # overridden per-request via _render(user=...)
        }
