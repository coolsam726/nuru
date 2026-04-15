"""Tests for nuru's role/permission system.

Coverage:
- default_permission_checker (both single-user and DB-mode)
- db_permission_checker (exact match + wildcards)
- DatabaseAuthBackend.authenticate / get_current_user / get_session_user_id
- AdminPanel.sync_permissions (upserts correct codenames)
- Resource._user_allowed (uses codenames, handles action_key fallback)
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Permission checker tests (pure-unit, no DB)
# ---------------------------------------------------------------------------


class TestDefaultPermissionChecker:
    """default_permission_checker — codename-based, with single-user fallback."""

    from nuru.auth import default_permission_checker as _check

    def test_none_user_denied(self):
        from nuru.auth import default_permission_checker
        assert default_permission_checker(None, "users:list") is False

    def test_single_user_mode_no_permissions_key(self):
        """SimpleAuthBackend user dict (no _permissions) → full access."""
        from nuru.auth import default_permission_checker
        user = {"username": "admin"}
        assert default_permission_checker(user, "users:delete") is True
        assert default_permission_checker(user, "orders:list") is True

    def test_empty_permissions_denies_all(self):
        from nuru.auth import default_permission_checker
        user = {"_permissions": set()}
        assert default_permission_checker(user, "users:list") is False

    def test_exact_match(self):
        from nuru.auth import default_permission_checker
        user = {"_permissions": {"users:list", "users:view"}}
        assert default_permission_checker(user, "users:list") is True
        assert default_permission_checker(user, "users:view") is True
        assert default_permission_checker(user, "users:delete") is False

    def test_superuser_wildcard(self):
        from nuru.auth import default_permission_checker
        user = {"_permissions": {"*"}}
        assert default_permission_checker(user, "users:delete") is True
        assert default_permission_checker(user, "orders:create") is True

    def test_resource_wildcard(self):
        from nuru.auth import default_permission_checker
        user = {"_permissions": {"users:*"}}
        assert default_permission_checker(user, "users:delete") is True
        assert default_permission_checker(user, "orders:list") is False

    def test_action_wildcard(self):
        from nuru.auth import default_permission_checker
        user = {"_permissions": {"*:list"}}
        assert default_permission_checker(user, "users:list") is True
        assert default_permission_checker(user, "orders:list") is True
        assert default_permission_checker(user, "users:delete") is False


class TestDbPermissionChecker:
    """db_permission_checker — same logic, different entry point."""

    def test_none_user(self):
        from nuru.roles import db_permission_checker
        assert db_permission_checker(None, "users:list") is False

    def test_exact_match(self):
        from nuru.roles import db_permission_checker
        user = {"_permissions": {"users:list"}}
        assert db_permission_checker(user, "users:list") is True
        assert db_permission_checker(user, "users:create") is False

    def test_superuser_wildcard(self):
        from nuru.roles import db_permission_checker
        user = {"_permissions": {"*"}}
        assert db_permission_checker(user, "anything:delete") is True

    def test_resource_wildcard(self):
        from nuru.roles import db_permission_checker
        user = {"_permissions": {"orders:*"}}
        assert db_permission_checker(user, "orders:delete") is True
        assert db_permission_checker(user, "users:delete") is False

    def test_action_wildcard(self):
        from nuru.roles import db_permission_checker
        user = {"_permissions": {"*:view"}}
        assert db_permission_checker(user, "users:view") is True
        assert db_permission_checker(user, "orders:view") is True
        assert db_permission_checker(user, "orders:delete") is False

    def test_object_with_permissions_attribute(self):
        """Supports user objects (not just dicts) with a _permissions attribute."""
        from nuru.roles import db_permission_checker
        user = MagicMock()
        user._permissions = {"users:list"}
        assert db_permission_checker(user, "users:list") is True
        assert db_permission_checker(user, "users:delete") is False


# ---------------------------------------------------------------------------
# DatabaseAuthBackend tests (asyncio)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDatabaseAuthBackend:

    def _make_backend(self, user, *, verify_password=None):
        """Build a backend with _fetch_user_by_username patched to return *user*."""
        from nuru.auth import DatabaseAuthBackend

        mock_table = MagicMock()
        mock_col = MagicMock()
        mock_col.key = "id"
        mock_col.type = MagicMock()
        mock_col.type.python_type = int
        mock_table.primary_key.columns = [mock_col]
        mock_model = MagicMock(__table__=mock_table, email="a@b.com")

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_factory = MagicMock(return_value=mock_session)

        backend = DatabaseAuthBackend(
            user_model=mock_model,
            session_factory=mock_factory,
            username_field="email",
            password_field="password",
            verify_password=verify_password,
            secret_key="test-secret",
        )
        # Patch the DB-touching helper directly so tests stay unit-level.
        backend._fetch_user_by_username = AsyncMock(return_value=user)
        return backend, mock_session, mock_factory

    async def test_authenticate_success_with_verify_fn(self):
        user = MagicMock(email="a@b.com", password="$hash")
        verify = MagicMock(return_value=True)
        backend, _, _ = self._make_backend(user, verify_password=verify)
        assert await backend.authenticate("a@b.com", "plain") is True
        verify.assert_called_once_with("plain", "$hash")

    async def test_authenticate_failure_with_verify_fn(self):
        user = MagicMock(email="a@b.com", password="$hash")
        verify = MagicMock(return_value=False)
        backend, _, _ = self._make_backend(user, verify_password=verify)
        assert await backend.authenticate("a@b.com", "wrong") is False

    async def test_authenticate_fallback_plaintext(self):
        """No verify_password → hmac.compare_digest fallback."""
        user = MagicMock(email="a@b.com", password="mypassword")
        backend, _, _ = self._make_backend(user)
        assert await backend.authenticate("a@b.com", "mypassword") is True
        assert await backend.authenticate("a@b.com", "wrong") is False

    async def test_authenticate_user_not_found(self):
        from nuru.auth import DatabaseAuthBackend

        mock_table = MagicMock()
        mock_table.primary_key.columns = []
        backend = DatabaseAuthBackend(
            user_model=MagicMock(__table__=mock_table),
            session_factory=MagicMock(),
            username_field="email",
            password_field="password",
            secret_key="test",
        )
        backend._fetch_user_by_username = AsyncMock(return_value=None)
        assert await backend.authenticate("nobody@x.com", "any") is False

    async def test_get_current_user_no_cookie(self):
        backend, _, _ = self._make_backend(MagicMock())
        request = MagicMock()
        request.cookies.get.return_value = None
        assert await backend.get_current_user(request) is None

    async def test_get_current_user_invalid_signature(self):
        backend, _, _ = self._make_backend(MagicMock())
        request = MagicMock()
        request.cookies.get.return_value = "invalid.token.garbage"
        assert await backend.get_current_user(request) is None

    async def test_set_and_clear_session(self):
        backend, _, _ = self._make_backend(MagicMock())
        response = MagicMock()
        backend.set_session(response, "42")
        response.set_cookie.assert_called_once()
        args, kwargs = response.set_cookie.call_args
        # The cookie value should be a signed string, not "42"
        assert kwargs.get("httponly") is True
        assert kwargs.get("samesite") == "lax"

        backend.clear_session(response)
        response.delete_cookie.assert_called_once()


# ---------------------------------------------------------------------------
# Resource._user_allowed tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestUserAllowed:

    def _make_resource(self, checker=None, auth=None):
        """Minimal resource wired to a panel with a controllable checker."""
        from nuru.resource import Resource

        class DemoResource(Resource):
            label = "Demo"
            slug = "demo"

        panel = MagicMock()
        panel.auth = auth or MagicMock()
        panel.permission_checker = checker
        panel._current_user = AsyncMock(return_value={"_permissions": {"demo:list", "demo:view"}})

        resource = DemoResource.__new__(DemoResource)
        resource.panel = panel
        resource.slug = "demo"
        return resource

    async def test_no_auth_always_allowed(self):
        resource = self._make_resource()
        resource.panel.auth = None
        assert await resource._user_allowed(MagicMock(), "delete") is True

    async def test_no_checker_always_allowed(self):
        resource = self._make_resource(checker=None)
        resource.panel.auth = MagicMock()
        assert await resource._user_allowed(MagicMock(), "delete") is True

    async def test_exact_codename_allowed(self):
        from nuru.roles import db_permission_checker
        resource = self._make_resource(checker=db_permission_checker)
        resource.panel._current_user = AsyncMock(return_value={"_permissions": {"demo:list"}})
        assert await resource._user_allowed(MagicMock(), "list") is True

    async def test_exact_codename_denied(self):
        from nuru.roles import db_permission_checker
        resource = self._make_resource(checker=db_permission_checker)
        resource.panel._current_user = AsyncMock(return_value={"_permissions": {"demo:list"}})
        assert await resource._user_allowed(MagicMock(), "delete") is False

    async def test_action_key_specific_granted(self):
        from nuru.roles import db_permission_checker
        resource = self._make_resource(checker=db_permission_checker)
        resource.panel._current_user = AsyncMock(
            return_value={"_permissions": {"demo:action:export_csv"}}
        )
        # Specific action key matches
        assert await resource._user_allowed(MagicMock(), "action", "export_csv") is True

    async def test_action_key_generic_fallback(self):
        from nuru.roles import db_permission_checker
        resource = self._make_resource(checker=db_permission_checker)
        resource.panel._current_user = AsyncMock(
            return_value={"_permissions": {"demo:action"}}
        )
        # Generic "demo:action" covers any named action
        assert await resource._user_allowed(MagicMock(), "action", "export_csv") is True
        assert await resource._user_allowed(MagicMock(), "action", "send_notice") is True

    async def test_action_key_denied(self):
        from nuru.roles import db_permission_checker
        resource = self._make_resource(checker=db_permission_checker)
        resource.panel._current_user = AsyncMock(return_value={"_permissions": {"demo:list"}})
        assert await resource._user_allowed(MagicMock(), "action", "export_csv") is False

    async def test_async_checker_supported(self):
        """Checker can be an async function."""
        async def async_checker(user, codename, resource):
            return codename == "demo:list"

        resource = self._make_resource(checker=async_checker)
        assert await resource._user_allowed(MagicMock(), "list") is True
        assert await resource._user_allowed(MagicMock(), "delete") is False


# ---------------------------------------------------------------------------
# STANDARD_ACTIONS and sync_permissions
# ---------------------------------------------------------------------------


def test_standard_actions_content():
    from nuru.roles import STANDARD_ACTIONS
    for expected in ("list", "view", "create", "edit", "delete", "action"):
        assert expected in STANDARD_ACTIONS


@pytest.mark.asyncio
async def test_sync_permissions_upserts_codenames():
    """sync_permissions should call session.add_all with the right codenames."""
    from nuru.panel import AdminPanel
    from nuru.resource import Resource
    from nuru.roles import STANDARD_ACTIONS

    class FooResource(Resource):
        label = "Foo"
        slug = "foo"
        label_plural = "Foos"

    panel = AdminPanel(title="Test", prefix="/test")
    panel.register(FooResource)

    added_items = []

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    existing_result = MagicMock()
    existing_result.all.return_value = []   # no existing permissions
    mock_session.exec = AsyncMock(return_value=existing_result)

    def capture_add_all(items):
        added_items.extend(items)

    mock_session.add_all = MagicMock(side_effect=capture_add_all)
    mock_session.commit = AsyncMock()

    await panel.sync_permissions(MagicMock(return_value=mock_session))

    added_codenames = {p.codename for p in added_items}
    for action in STANDARD_ACTIONS:
        assert f"foo:{action}" in added_codenames, f"Missing codename foo:{action}"
    assert "*" in added_codenames  # superuser wildcard always included
