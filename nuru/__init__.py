# Legacy imports (kept for backward compatibility)
from .panel import AdminPanel
from .resource import Resource as _LegacyResource
from .page import Page as _LegacyPage
from . import columns
from . import fields
from . import actions as _actions_legacy

# New v0.4 API
from .panels import Panel
from .resources import Resource
from .pages import Page, ListPage, CreatePage, EditPage, ViewPage
from .forms.base import Form
from .forms import components as form_components
from .tables import Table
from .tables import columns as table_columns
from .infolists import Infolist
from .infolists import components as infolist_components
from .actions import Action, CreateAction, EditAction, DeleteAction, ViewAction

from .auth import AuthBackend, SimpleAuthBackend, DatabaseAuthBackend, default_permission_checker
from .roles import Permission, Role, RolePermission, UserRole, db_permission_checker, STANDARD_ACTIONS
from .migrations import sync_schema
from .icons import resolve_icon, render_icon

__all__ = [
    # v0.4 API
    "Panel",
    "Resource",
    "Page", "ListPage", "CreatePage", "EditPage", "ViewPage",
    "Form",
    "Table",
    "Infolist",
    "Action", "CreateAction", "EditAction", "DeleteAction", "ViewAction",
    "form_components",
    "table_columns",
    "infolist_components",
    # Legacy
    "AdminPanel",
    "columns",
    "fields",
    # Auth backends
    "AuthBackend",
    "SimpleAuthBackend",
    "DatabaseAuthBackend",
    # Permission checkers
    "default_permission_checker",
    "db_permission_checker",
    # Role / permission models
    "Permission",
    "Role",
    "RolePermission",
    "UserRole",
    "STANDARD_ACTIONS",
    # Utilities
    "sync_schema",
    "resolve_icon",
    "render_icon",
]
__version__ = "0.1.0"
