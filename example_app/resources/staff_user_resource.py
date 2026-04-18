from typing import Any

from nuru import forms
from nuru.columns import Text, Badge, Boolean, Image, Currency, DateTime
from nuru import Role, UserRole
from nuru.resources.base import Resource
from nuru.forms.base import Form
from nuru.tables.base import Table
from sqlmodel import select as sm_select

from example_app.models import StaffUser
from example_app.db import get_session


class _StaffUserView:
    def __init__(self, user: StaffUser, role_ids: list[str],
                 roles_list: list[str], all_roles: list[dict]):
        for attr in ("id", "name", "email", "password", "role", "active"):
            setattr(self, attr, getattr(user, attr))
        self.role_ids   = role_ids
        self.roles_list = roles_list
        self.all_roles  = all_roles

    def __str__(self) -> str:
        return self.name


class StaffUserResource(Resource):
    label = "Staff User"
    label_plural = "Staff Users"
    nav_sort = 70
    nav_icon = "shield-check"
    model = StaffUser
    session_factory = get_session
    search_fields = ["name", "email"]
    form_cols = 2

    def table(self) -> Table:
        return Table().schema([
            Text("name",  "Name",  sortable=True),
            Text("email", "Email"),
            Badge("role", "Display Role", colors={
                "admin": "purple", "librarian": "blue", "viewer": "gray",
            }),
            Boolean("active", "Active"),
        ])

    def form(self) -> Form:
        return Form().schema([
            forms.Section(
                [
                    forms.TextInput.make("name").label("Full name").required(),
                    forms.TextInput.make("email").email().label("Email address").required(),
                    forms.Password("password").label("Password").help_text("Leave blank to keep current password."),
                    forms.Select.make("role").label("Display role").options(["admin", "librarian", "viewer"]).help_text("Badge only — actual access controlled via Roles below."),
                    forms.Checkbox.make("active").label("Active"),
                ],
                title="Account", cols=2, col_span="full",
            ),
            forms.Fieldset(
                [
                    forms.CheckboxGroup("role_ids").label("").options_from("all_roles").col_span("full"),
                ],
                title="Assigned Roles",
                description="Grant this user role-based permissions.",
                col_span="full", cols=1,
            ),
        ])

    async def get_record(self, id: Any) -> _StaffUserView | None:
        async with get_session() as session:
            user = await session.get(StaffUser, int(id))
            if user is None:
                return None
            all_roles_rows = (await session.exec(sm_select(Role))).all()
            all_roles = [
                {"value": str(r.id), "label": r.name}
                for r in sorted(all_roles_rows, key=lambda r: r.name)
            ]
            user_roles = (
                await session.exec(sm_select(UserRole).where(UserRole.user_id == str(user.id)))
            ).all()
            assigned_ids = [str(ur.role_id) for ur in user_roles]
            role_names   = [r.name for r in all_roles_rows if str(r.id) in assigned_ids]
            return _StaffUserView(user, assigned_ids, sorted(role_names), all_roles)

    async def after_save(self, record_id: Any, data: dict) -> None:
        selected_ids = {int(v) for v in (data.get("role_ids") or []) if v}
        async with get_session() as session:
            user_id  = str(record_id)
            existing = (await session.exec(sm_select(UserRole).where(UserRole.user_id == user_id))).all()
            existing_ids = {ur.role_id for ur in existing}
            for role_id in selected_ids - existing_ids:
                session.add(UserRole(user_id=user_id, role_id=role_id))
            for ur in existing:
                if ur.role_id not in selected_ids:
                    await session.delete(ur)
            await session.commit()

