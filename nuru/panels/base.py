"""nuru.panels.base — Panel base class."""
from __future__ import annotations
import importlib.util
import inspect
from pathlib import Path
from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from fastapi import FastAPI


class Panel:
    """Base class for all Nuru panels.  Subclass to create your admin panel."""
    # Class-level defaults — override in subclasses
    title: str = "Admin"
    prefix: str = "/admin"
    primary_color: str | None = None
    auth_backend: Any = None
    permission_checker: Any = None
    per_page: int = 25
    upload_dir: str | Path | None = None
    upload_backend: Any = None

    def __init__(self) -> None:
        cls = self.__class__

        # Helper: read a class attribute only if a *subclass* explicitly declares it
        # as a non-callable value (i.e. not the fluent-setter method defined on Panel).
        def _cv(name: str, default: Any = None) -> Any:
            for klass in cls.__mro__:
                if klass is Panel:
                    break  # don't read Panel's own method definitions
                if name in vars(klass):
                    val = vars(klass)[name]
                    if not callable(val) or isinstance(val, (type, staticmethod, classmethod)):
                        return val
            return default

        self._title: str = _cv("title", "Admin")
        self._prefix: str = _cv("prefix", "/admin").rstrip("/")
        self._primary_color: str | None = _cv("primary_color", None)
        self._auth_backend: Any = _cv("auth_backend", None)
        self._permission_checker: Any = _cv("permission_checker", None)
        self._per_page: int = _cv("per_page", 25)
        self._upload_dir: Any = _cv("upload_dir", None)
        self._upload_backend: Any = _cv("upload_backend", None)
        self._resource_classes: list[type] = []
        self._page_classes: list[type] = []
        self._extra_template_dirs: list[Path] = []
        self._extra_js: list[str] = []
        self._extra_css: list[str] = []

        # Auto-register any class-level resource/page lists defined on subclass
        for attr in ("resources", "resource_classes"):
            val = getattr(cls, attr, None)
            if val and isinstance(val, (list, tuple)):
                self._resource_classes.extend(val)
        for attr in ("pages", "page_classes"):
            val = getattr(cls, attr, None)
            if val and isinstance(val, (list, tuple)):
                self._page_classes.extend(val)
    # ------------------------------------------------------------------ #
    # Factory                                                              #
    # ------------------------------------------------------------------ #
    @classmethod
    def make(cls) -> "Panel":
        return cls()
    # ------------------------------------------------------------------ #
    # Fluent setters                                                       #
    # ------------------------------------------------------------------ #
    def title(self, value: str) -> "Panel":           # type: ignore[override]
        self._title = value; return self
    def prefix(self, value: str) -> "Panel":          # type: ignore[override]
        self._prefix = value.rstrip("/"); return self
    def primary_color(self, value: str) -> "Panel":   # type: ignore[override]
        self._primary_color = value; return self
    def auth_backend(self, value: Any) -> "Panel":    # type: ignore[override]
        self._auth_backend = value; return self
    def permission_checker(self, value: Any) -> "Panel":  # type: ignore[override]
        self._permission_checker = value; return self
    def per_page(self, value: int) -> "Panel":        # type: ignore[override]
        self._per_page = value; return self
    def upload_dir(self, value: Any) -> "Panel":      # type: ignore[override]
        self._upload_dir = value; return self
    def upload_backend(self, value: Any) -> "Panel":  # type: ignore[override]
        self._upload_backend = value; return self
    # ------------------------------------------------------------------ #
    # Getters                                                              #
    # ------------------------------------------------------------------ #
    def get_title(self) -> str: return self._title
    def get_prefix(self) -> str: return self._prefix
    def get_primary_color(self) -> str | None: return self._primary_color
    def get_auth_backend(self): return self._auth_backend
    def get_permission_checker(self): return self._permission_checker
    def get_per_page(self) -> int: return self._per_page
    def get_upload_dir(self): return self._upload_dir
    def get_upload_backend(self): return self._upload_backend
    def get_resource_classes(self) -> list[type]: return list(self._resource_classes)
    def get_page_classes(self) -> list[type]: return list(self._page_classes)
    # ------------------------------------------------------------------ #
    # Registration                                                         #
    # ------------------------------------------------------------------ #
    def register(self, resource_class: type) -> "Panel":
        """Register a Resource subclass."""
        if resource_class not in self._resource_classes:
            self._resource_classes.append(resource_class)
        return self
    def register_page(self, page_class: type) -> "Panel":
        """Register a Page subclass."""
        if page_class not in self._page_classes:
            self._page_classes.append(page_class)
        return self
    def add_template_dir(self, path: str | Path) -> "Panel":
        """Register an additional template directory."""
        self._extra_template_dirs.append(Path(path)); return self
    def add_extra_js(self, url: str) -> "Panel":
        """Register an additional JS URL to inject into every page."""
        self._extra_js.append(url); return self
    def add_extra_css(self, url: str) -> "Panel":
        """Register an additional CSS URL to inject into every page."""
        self._extra_css.append(url); return self
    # ------------------------------------------------------------------ #
    # Auto-discovery                                                       #
    # ------------------------------------------------------------------ #
    def _discover(self) -> None:
        """Scan sibling resources/ and pages/ directories for subclasses."""
        from nuru.resources.base import Resource
        from nuru.pages.base import Page
        # Find the file that defines this Panel subclass
        cls = self.__class__
        if cls is Panel:
            return  # nothing to discover on the base class itself
        try:
            panel_file = Path(inspect.getfile(cls))
        except (TypeError, OSError):
            return
        panel_pkg_dir = panel_file.parent
        self._discover_in(panel_pkg_dir / "resources", Resource, self._resource_classes)
        self._discover_in(panel_pkg_dir / "pages", Page, self._page_classes)
    @staticmethod
    def _discover_in(directory: Path, base_class: type, target: list) -> None:
        """Import all .py files in *directory* and collect subclasses of *base_class*."""
        if not directory.is_dir():
            return
        for py_file in sorted(directory.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            module_name = f"_nuru_discover_{py_file.stem}_{id(py_file)}"
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)  # type: ignore[attr-defined]
            except Exception:
                continue
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, base_class) and obj is not base_class and obj not in target:
                    target.append(obj)
    # ------------------------------------------------------------------ #
    # Mount                                                                #
    # ------------------------------------------------------------------ #
    def mount(self, app: "FastAPI") -> None:
        """Auto-discover resources/pages then wire all routes onto *app*."""
        self._discover()
        from nuru.panel import AdminPanel as _AdminPanel
        legacy = _AdminPanel(
            title=self._title,
            prefix=self._prefix,
            primary=self._primary_color,
            auth=self._auth_backend,
            permission_checker=self._permission_checker,
            per_page=self._per_page,
            upload_dir=self._upload_dir,
            upload_backend=self._upload_backend,
            extra_js=self._extra_js,
            extra_css=self._extra_css,
        )
        # Register discovered resources and pages
        for rc in self._resource_classes:
            legacy.register(rc)
        for pc in self._page_classes:
            legacy.register_page(pc)
        # Extra template dirs (e.g. from components)
        for d in self._extra_template_dirs:
            legacy.add_template_dir(str(d))
        legacy.mount(app)
        # Store reference for later use (e.g. upload_dir)
        self._legacy = legacy
    def __repr__(self) -> str:
        return f"{type(self).__name__}(prefix={self._prefix!r}, title={self._title!r})"
