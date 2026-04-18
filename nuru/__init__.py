# ---------------------------------------------------------------------------
# Nuru public API
# ---------------------------------------------------------------------------

# Core classes
from .panels import Panel
from .resources import Resource
from .pages import Page, ListPage, CreatePage, EditPage, ViewPage
from .forms.base import Form
from . import forms
from .tables import Table
from . import columns
from .columns import Column, Text, Badge, Boolean, Currency, DateTime, Image
from .infolists import Infolist
from .infolists import components as infolist_components
from .forms import components as form_components
from .actions import Action, CreateAction, EditAction, DeleteAction, ViewAction

# Auth
from .auth import AuthBackend, SimpleAuthBackend, DatabaseAuthBackend, default_permission_checker
from .roles import Permission, Role, RolePermission, UserRole, db_permission_checker, STANDARD_ACTIONS
from .migrations import sync_schema
from .icons import resolve_icon, render_icon

__all__ = [
    # Core
    "Panel",
    "Resource",
    "Page", "ListPage", "CreatePage", "EditPage", "ViewPage",
    "Form",
    "Table",
    "Infolist",
    "Action", "CreateAction", "EditAction", "DeleteAction", "ViewAction",
    # Namespaces
    "forms",
    "columns",
    "form_components",
    "infolist_components",
    # Individual column classes
    "Column", "Text", "Badge", "Boolean", "Currency", "DateTime", "Image",
    # Auth
    "AuthBackend",
    "SimpleAuthBackend",
    "DatabaseAuthBackend",
    "default_permission_checker",
    "db_permission_checker",
    # Roles / permissions
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
__version__ = "0.3.1"
