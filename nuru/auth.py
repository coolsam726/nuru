from __future__ import annotations

import hmac
from abc import ABC, abstractmethod
from typing import Any

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
# Basic role/permission helper
#
# Provide a conservative, easily-replaceable default permission checker that
# understands a small role hierarchy (admin > editor > viewer). Backends that
# integrate with a user database may return richer user objects (with a
# ``role`` attribute) and can supply a custom permission checker to
# ``AdminPanel`` during construction.
# ---------------------------------------------------------------------------


ROLE_RANK: dict[str, int] = {
    "viewer": 10,
    "editor": 20,
    "admin": 30,
}


def default_permission_checker(user: Any | None, action: str, resource: object | None = None) -> bool:
    """
    Default permission policy.

    - If *user* is None, deny access.
    - If *user* exposes a ``role`` attribute or mapping key, use the role
      rank to determine permission: admins can do everything, editors can
      create/edit but not necessarily delete, viewers can only view/list.
    - If *user* contains no role information (e.g. the built-in
      ``SimpleAuthBackend`` returns a simple dict with only a username),
      treat the session as an admin for compatibility with single-user
      setups.

    This function is intentionally simple and meant to be replaced by a
    project-specific checker for production deployments.
    """
    if user is None:
        return False

    # Extract role from object or mapping
    role = None
    try:
        if isinstance(user, dict):
            role = user.get("role")
        else:
            role = getattr(user, "role", None)
    except Exception:
        role = None

    # No role -> assume single-user admin (compatibility)
    if not role:
        return True

    rank = ROLE_RANK.get(str(role), 0)

    if action in ("view", "list"):
        return rank >= ROLE_RANK.get("viewer", 10)
    if action in ("create", "edit"):
        return rank >= ROLE_RANK.get("editor", 20)
    if action in ("delete",):
        return rank >= ROLE_RANK.get("admin", 30)
    if action.startswith("action:"):
        # Generic actions require at least editor by default
        return rank >= ROLE_RANK.get("editor", 20)

    # Unknown actions — be conservative and deny.
    return False
