"""
Role / Permission models and the default DB-backed permission checker.

Architecture
------------
Permissions are fixed codenames scoped to a resource and action::

    users:list      users:view      users:create
    users:edit      users:delete    users:action

The special codename ``*`` is a superuser grant (allows everything).
Wildcards ``{slug}:*`` and ``*:{action}`` are also supported.

Roles are user-defined groupings of permissions (Many:Many).
Users are assigned roles (Many:Many) via ``UserRole``.
The effective set of permissions for a user is the union of all permissions
attached to all of their roles.

Database tables
---------------
All table names are prefixed with ``nuru_`` to avoid clashing with application
tables. ``user_id`` in ``UserRole`` is stored as a plain string (str(pk)) so
the nuru tables carry no foreign-key dependency on — and therefore no
knowledge of — the application's user table.

Usage
-----
1. Include ``nuru.roles`` models in your ``SQLModel.metadata`` by importing
   them *before* ``sync_schema`` or ``SQLModel.metadata.create_all``::

       import nuru.roles  # registers Permission, Role, etc. with SQLModel

2. Call ``await panel.sync_permissions(session_factory)`` at startup to
   upsert the permission rows for every registered resource.

3. Wire up :class:`~nuru.auth.DatabaseAuthBackend` and pass
   :func:`db_permission_checker` as the ``permission_checker`` to your
   :class:`~nuru.panel.AdminPanel`::

       from nuru.roles import db_permission_checker

       panel = AdminPanel(
           auth=DatabaseAuthBackend(...),
           permission_checker=db_permission_checker,
       )
"""
from __future__ import annotations

from typing import Any, Optional

from sqlmodel import Field, SQLModel

# ---------------------------------------------------------------------------
# Standard per-resource action codename suffixes
# ---------------------------------------------------------------------------

STANDARD_ACTIONS: list[str] = [
    "list",
    "view",
    "create",
    "edit",
    "delete",
    "action",   # generic — covers all named actions unless overridden
]


# ---------------------------------------------------------------------------
# SQLModel table definitions
# ---------------------------------------------------------------------------


class Permission(SQLModel, table=True):
    """A single, fixed permission codename (e.g. ``users:list``)."""

    __tablename__ = "nuru_permission"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    codename: str = Field(unique=True, index=True)
    """Machine-readable identifier, e.g. ``users:list`` or ``*``."""
    label: str = Field(default="")
    """Human-readable description shown in the admin UI."""


class Role(SQLModel, table=True):
    """A named group of permissions that can be assigned to users."""

    __tablename__ = "nuru_role"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    description: str = Field(default="")


class RolePermission(SQLModel, table=True):
    """Many-to-many join: which permissions belong to a role."""

    __tablename__ = "nuru_role_permission"  # type: ignore[assignment]

    role_id: int = Field(foreign_key="nuru_role.id", primary_key=True)
    permission_id: int = Field(foreign_key="nuru_permission.id", primary_key=True)


class UserRole(SQLModel, table=True):
    """Many-to-many join: which roles a user holds.

    ``user_id`` is stored as a plain string (``str(user.pk)``) so nuru carries
    no foreign-key dependency on the application's user table.
    """

    __tablename__ = "nuru_user_role"  # type: ignore[assignment]

    user_id: str = Field(primary_key=True)
    role_id: int = Field(foreign_key="nuru_role.id", primary_key=True)


# ---------------------------------------------------------------------------
# Helper: fetch all permission codenames for a user from the database
# ---------------------------------------------------------------------------


async def get_user_permissions(user_id: str, session_factory: Any) -> set[str]:
    """Return the set of permission codenames held by *user_id*.

    This is used by :class:`~nuru.auth.DatabaseAuthBackend` when building
    the user dict returned by ``get_current_user``.
    """
    from sqlmodel import select

    async with session_factory() as session:
        role_id_stmt = select(UserRole.role_id).where(UserRole.user_id == user_id)
        role_ids = list((await session.exec(role_id_stmt)).all())

        if not role_ids:
            return set()

        perm_id_stmt = select(RolePermission.permission_id).where(
            RolePermission.role_id.in_(role_ids)  # type: ignore[arg-type]
        )
        perm_ids = list((await session.exec(perm_id_stmt)).all())

        if not perm_ids:
            return set()

        codename_stmt = select(Permission.codename).where(
            Permission.id.in_(perm_ids)  # type: ignore[arg-type]
        )
        codenames = list((await session.exec(codename_stmt)).all())

    return set(codenames)


# ---------------------------------------------------------------------------
# DB-backed permission checker
# ---------------------------------------------------------------------------


def db_permission_checker(
    user: Any | None,
    codename: str,
    resource: Any | None = None,
) -> bool:
    """Check whether *user* holds *codename*.

    The user dict/object must contain ``_permissions: set[str]`` — populated
    automatically by :class:`~nuru.auth.DatabaseAuthBackend`.

    Supported wildcard expansions (checked in order):

    1. ``*``               — superuser; allows everything
    2. ``{slug}:{action}`` — exact match
    3. ``{slug}:*``        — all actions on this resource
    4. ``*:{action}``      — this action on all resources
    """
    if user is None:
        return False

    if isinstance(user, dict):
        perms: set[str] = user.get("_permissions", set())  # type: ignore[assignment]
    else:
        perms = getattr(user, "_permissions", set())

    if "*" in perms:
        return True

    if codename in perms:
        return True

    parts = codename.split(":", 1)
    if len(parts) == 2:
        slug, action = parts
        if f"{slug}:*" in perms:
            return True
        if f"*:{action}" in perms:
            return True

    return False
