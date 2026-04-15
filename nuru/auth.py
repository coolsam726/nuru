from __future__ import annotations

import hmac
from abc import ABC, abstractmethod
from typing import Any, Callable

from fastapi import Request
from fastapi.responses import Response
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner


class AuthBackend(ABC):
    """
    Abstract authentication backend.

    Subclass this and pass an instance to :class:`~nuru.AdminPanel`::

        panel = AdminPanel(title="My Admin", auth=MyAuthBackend(...))

    The simplest built-in backend is :class:`SimpleAuthBackend`.
    """

    @abstractmethod
    async def authenticate(self, username: str, password: str) -> bool:
        """Return ``True`` if *username* / *password* are valid credentials."""
        ...

    @abstractmethod
    async def get_current_user(self, request: Request) -> Any | None:
        """
        Return the current user object if the request is authenticated,
        otherwise return ``None``.

        The returned value is available in templates as ``current_user``.
        """
        ...

    def set_session(self, response: Response, user_id: str) -> None:
        """Write the session cookie onto *response* after a successful login."""

    def clear_session(self, response: Response) -> None:
        """Remove the session cookie from *response* on logout."""

    async def get_session_user_id(self, username: str) -> str:
        """Return the value to store in the session cookie after a successful login.

        The default implementation stores the *username* string itself, which
        is correct for :class:`SimpleAuthBackend`.

        Override in database-backed backends to look up and return the user's
        primary key so that ``get_current_user`` can perform a PK-based lookup
        rather than a username search on every request.
        """
        return username


class SimpleAuthBackend(AuthBackend):
    """
    A single-user, signed-cookie auth backend suitable for personal or
    internal admin panels.

    For multi-user setups, subclass :class:`AuthBackend` and implement your
    own user lookup against a database or directory service.

    Usage::

        from nuru.auth import SimpleAuthBackend

        panel = AdminPanel(
            title="My Admin",
            auth=SimpleAuthBackend(
                username="admin",
                password="s3cr3t",
                secret_key="change-me-to-a-long-random-string",
            ),
        )

    .. warning::
        Set *secret_key* to a long, random value in production.  The cookie is
        signed (not encrypted) — anyone with the secret key can forge sessions.
    """

    COOKIE_NAME = "ap_session"

    def __init__(
        self,
        *,
        username: str,
        password: str,
        secret_key: str,
        max_age: int = 86_400,  # 24 hours
    ) -> None:
        self._username = username
        self._password = password
        self._signer = TimestampSigner(secret_key)
        self._max_age = max_age

    async def authenticate(self, username: str, password: str) -> bool:
        # Use constant-time compare to prevent timing attacks.
        return hmac.compare_digest(username, self._username) and hmac.compare_digest(
            password, self._password
        )

    async def get_current_user(self, request: Request) -> dict | None:
        token = request.cookies.get(self.COOKIE_NAME)
        if not token:
            return None
        try:
            value = self._signer.unsign(token, max_age=self._max_age).decode()
            return {"username": value}
        except (BadSignature, SignatureExpired):
            return None

    def set_session(self, response: Response, user_id: str) -> None:
        token = self._signer.sign(user_id).decode()
        response.set_cookie(
            self.COOKIE_NAME,
            token,
            httponly=True,
            samesite="lax",
            max_age=self._max_age,
        )

    def clear_session(self, response: Response) -> None:
        response.delete_cookie(self.COOKIE_NAME)


# ---------------------------------------------------------------------------
# Default (non-database) permission checker
#
# Works entirely from the ``_permissions`` set cached on the user dict by
# DatabaseAuthBackend.get_current_user.  If the user has no ``_permissions``
# key (e.g. when using SimpleAuthBackend which returns only a username dict),
# the single-user fallback grants full access so that simple deployments
# require zero extra config.
#
# The codename format is ``{resource_slug}:{action}``, e.g. ``users:list``.
# Wildcards: ``*`` (superuser), ``{slug}:*``, ``*:{action}``.
# ---------------------------------------------------------------------------


def default_permission_checker(
    user: Any | None,
    codename: str,
    resource: object | None = None,
) -> bool:
    """Evaluate *codename* against the authenticated *user*.

    When paired with :class:`DatabaseAuthBackend` the user dict carries
    ``_permissions`` and this function performs a pure set-membership check
    with wildcard support.

    When paired with :class:`SimpleAuthBackend` the user dict contains only
    ``username`` and no ``_permissions`` key — in that case all access is
    granted (single-user / internal admin pattern).
    """
    if user is None:
        return False

    # Fetch the cached permission set.
    if isinstance(user, dict):
        perms: set[str] | None = user.get("_permissions")  # type: ignore[assignment]
    else:
        perms = getattr(user, "_permissions", None)

    # No _permissions key → single-user backend: grant everything.
    if perms is None:
        return True

    # Superuser wildcard.
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


# ---------------------------------------------------------------------------
# Database-backed authentication backend
# ---------------------------------------------------------------------------


class DatabaseAuthBackend(AuthBackend):
    """Multi-user auth backend that authenticates against a database and
    loads permissions via nuru's role/permission tables.

    Requires the following nuru tables to exist in the database:
    ``nuru_permission``, ``nuru_role``, ``nuru_role_permission``,
    ``nuru_user_role``.  Call ``await panel.sync_permissions(session_factory)``
    or ``import nuru.roles`` before ``sync_schema`` to ensure the tables are
    created.

    Usage::

        from passlib.context import CryptContext
        from nuru.auth import DatabaseAuthBackend
        from nuru.roles import db_permission_checker

        _pwd = CryptContext(schemes=["bcrypt"])

        panel = AdminPanel(
            auth=DatabaseAuthBackend(
                user_model=User,
                session_factory=get_session,
                username_field="email",
                verify_password=_pwd.verify,
                secret_key=settings.SECRET_KEY,
            ),
            permission_checker=db_permission_checker,
        )

    The user dict returned by ``get_current_user`` includes:

    * ``id``         — str(user.pk)
    * ``username``   — value of *username_field*
    * ``_permissions`` — ``set[str]`` of resolved permission codenames
    * any extra fields listed in *extra_fields*

    .. warning::
        Never store plain-text passwords in production.  Pass a proper
        ``verify_password`` callable (e.g. from passlib or cryptography).
    """

    COOKIE_NAME = "ap_session"

    def __init__(
        self,
        *,
        user_model: Any,
        session_factory: Any,
        username_field: str = "username",
        password_field: str = "password",
        verify_password: Callable[[str, str], bool] | None = None,
        secret_key: str,
        max_age: int = 86_400,
        extra_fields: list[str] | None = None,
    ) -> None:
        self._user_model = user_model
        self._session_factory = session_factory
        self._username_field = username_field
        self._password_field = password_field
        self._verify_password = verify_password
        self._signer = TimestampSigner(secret_key)
        self._max_age = max_age
        self._extra_fields = extra_fields or []

    # ------------------------------------------------------------------
    # AuthBackend interface
    # ------------------------------------------------------------------

    async def authenticate(self, username: str, password: str) -> bool:
        """Return ``True`` if *username* / *password* are valid credentials."""
        user = await self._fetch_user_by_username(username)
        if user is None:
            return False
        stored = getattr(user, self._password_field, None)
        if stored is None:
            return False
        if self._verify_password is not None:
            return bool(self._verify_password(password, stored))
        # Fallback: constant-time plain-text compare (dev only).
        return hmac.compare_digest(password, str(stored))

    async def get_current_user(self, request: Request) -> dict | None:
        """Unsign the session cookie, load the user from the DB, resolve
        their role permissions, and return an enriched user dict."""
        token = request.cookies.get(self.COOKIE_NAME)
        if not token:
            return None
        try:
            user_id = self._signer.unsign(token, max_age=self._max_age).decode()
        except (BadSignature, SignatureExpired):
            return None

        user = await self._fetch_user_by_id(user_id)
        if user is None:
            return None

        from .roles import get_user_permissions
        perms = await get_user_permissions(user_id, self._session_factory)

        user_dict: dict[str, Any] = {
            "id": user_id,
            "username": getattr(user, self._username_field, user_id),
            "_permissions": perms,
        }
        for field in self._extra_fields:
            val = getattr(user, field, None)
            if val is not None:
                user_dict[field] = val
        return user_dict

    async def get_session_user_id(self, username: str) -> str:
        """Return str(user.pk) so the signed cookie stores the PK, not the
        username string."""
        user = await self._fetch_user_by_username(username)
        if user is None:
            return username  # should not happen, but degrade gracefully
        try:
            pk_cols = list(self._user_model.__table__.primary_key.columns)
            pk_name = pk_cols[0].key if pk_cols else "id"
        except AttributeError:
            pk_name = "id"
        return str(getattr(user, pk_name, username))

    def set_session(self, response: Response, user_id: str) -> None:
        token = self._signer.sign(user_id).decode()
        response.set_cookie(
            self.COOKIE_NAME,
            token,
            httponly=True,
            samesite="lax",
            max_age=self._max_age,
        )

    def clear_session(self, response: Response) -> None:
        response.delete_cookie(self.COOKIE_NAME)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _fetch_user_by_username(self, username: str) -> Any | None:
        from sqlmodel import select
        async with self._session_factory() as session:
            stmt = select(self._user_model).where(
                getattr(self._user_model, self._username_field) == username
            )
            return (await session.exec(stmt)).first()

    async def _fetch_user_by_id(self, user_id: str) -> Any | None:
        """Fetch by primary key, trying int coercion first."""
        async with self._session_factory() as session:
            try:
                pk_cols = list(self._user_model.__table__.primary_key.columns)
                pk_name = pk_cols[0].key if pk_cols else "id"
                pk_type = pk_cols[0].type.python_type if pk_cols else str
            except (AttributeError, NotImplementedError):
                pk_name, pk_type = "id", str
            try:
                coerced_id = pk_type(user_id)
            except (ValueError, TypeError):
                coerced_id = user_id  # type: ignore[assignment]
            return await session.get(self._user_model, coerced_id)
