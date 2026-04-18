from typing import Any

from nuru import columns, forms
from nuru import Role, Permission, RolePermission
from nuru.resources.base import Resource
from nuru.forms.base import Form
from nuru.tables.base import Table
from sqlmodel import select as sm_select

from example_app.db import get_session


class _RoleView:
    def __init__(self, role: Role, codenames: list[str], all_perms: list[dict]):
        for attr in ("id", "name", "description"):
            setattr(self, attr, getattr(role, attr))
        self.permission_ids  = [p["value"] for p in all_perms if p["label"] in codenames]
        self.all_permissions = all_perms
        self.permissions_list = sorted(codenames)

    def __str__(self) -> str:
        return self.name


class RoleResource(Resource):
    label = "Role"
    label_plural = "Roles"
    nav_sort = 80
    nav_icon = "lock-closed"
    model = Role
    session_factory = get_session
    search_fields = ["name", "description"]

    def table(self) -> Table:
        return Table().schema([
            columns.Text("name",        "Role Name",   sortable=True),
            columns.Text("description", "Description"),
        ])

    def form(self) -> Form:
        return Form().schema([
            forms.Section(
                [
                    forms.TextInput.make("name").label("Role name").required().placeholder("e.g. Librarian"),
                    forms.TextInput.make("description").label("Description").placeholder("What this role can do"),
                ],
                title="Role", cols=2, col_span="full",
            ),
            forms.Fieldset(
                [
                    forms.CheckboxGroup("permission_ids").label("").options_from("all_permissions").col_span("full"),
                ],
                title="Permissions",
                description="Permissions granted to members of this role. The * wildcard grants everything.",
                col_span="full", cols=1,
            ),
        ])

    async def get_record(self, id: Any) -> _RoleView | None:
        async with get_session() as session:
            role = await session.get(Role, int(id))
            if role is None:
                return None
            all_perms_rows = (await session.exec(sm_select(Permission))).all()
            all_perms = [
                {"value": str(p.id), "label": p.codename}
                for p in sorted(all_perms_rows, key=lambda p: p.codename)
            ]
            role_perms = (
                await session.exec(sm_select(RolePermission).where(RolePermission.role_id == role.id))
            ).all()
            assigned_ids = {rp.permission_id for rp in role_perms}
            codenames    = [p.codename for p in all_perms_rows if p.id in assigned_ids]
            return _RoleView(role, codenames, all_perms)

    async def after_save(self, record_id: Any, data: dict) -> None:
        selected_ids = {int(v) for v in (data.get("permission_ids") or []) if v}
        async with get_session() as session:
            role_id  = int(record_id)
            existing = (await session.exec(sm_select(RolePermission).where(RolePermission.role_id == role_id))).all()
            existing_ids = {rp.permission_id for rp in existing}
            # Preserve wildcard — cannot be removed through the UI
            if existing_ids:
                wildcard_perms = (
                    await session.exec(
                        sm_select(Permission).where(
                            Permission.id.in_(existing_ids), Permission.codename == "*"
                        )
                    )
                ).all()
                for wp in wildcard_perms:
                    selected_ids.add(wp.id)
            for perm_id in selected_ids - existing_ids:
                session.add(RolePermission(role_id=role_id, permission_id=perm_id))
            for rp in existing:
                if rp.permission_id not in selected_ids:
                    await session.delete(rp)
            await session.commit()

