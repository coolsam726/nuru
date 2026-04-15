"""
Minimal nuru demo for PythonAnywhere (free tier).

Upload this file to ~/nuru_demo/pa_app.py on PythonAnywhere.
The pa_wsgi.py file in the same directory acts as the WSGI entry point.

Credentials
-----------
  admin@demo.com / secret
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlmodel import SQLModel, Field as SMField, select as sm_select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

import nuru.roles  # registers Permission, Role, RolePermission, UserRole with SQLModel
from nuru import (
    AdminPanel, Resource,
    DatabaseAuthBackend,
    db_permission_checker,
    Permission, Role, RolePermission, UserRole,
    columns, fields,
)

# ── Database ──────────────────────────────────────────────────────────────────
# Store the DB alongside this file on PythonAnywhere.
_DB_PATH = Path(__file__).parent / "demo.db"
_engine  = create_async_engine(f"sqlite+aiosqlite:///{_DB_PATH}", echo=False)
_session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


# ── Auth model ────────────────────────────────────────────────────────────────
class AdminUser(SQLModel, table=True):
    __tablename__ = "admin_users"
    id:       int | None = SMField(default=None, primary_key=True)
    username: str        = SMField(index=True, unique=True)
    password: str
    is_active: bool      = True


async def _get_session():
    return _session_factory()


# ── Panels ────────────────────────────────────────────────────────────────────
auth = DatabaseAuthBackend(
    session_factory=_session_factory,
    model=AdminUser,
    username_field="username",
    password_field="password",
)

panel = AdminPanel(
    prefix="/admin",
    title="Nuru Demo",
    auth=auth,
    permission_checker=db_permission_checker(_session_factory),
)


# ── Resources — register your own here ───────────────────────────────────────
class RoleResource(Resource):
    label        = "Role"
    label_plural = "Roles"
    model        = Role
    session_factory = _session_factory
    can_delete   = False


panel.register(RoleResource)


# ── Lifespan: create tables + seed ───────────────────────────────────────────
@asynccontextmanager
async def _lifespan(app: FastAPI):
    from nuru.migrations import sync_schema

    await sync_schema(_engine, SQLModel.metadata)
    await panel.sync_permissions(_session_factory)

    async with _session_factory() as session:
        if not (await session.exec(sm_select(AdminUser))).first():
            session.add(AdminUser(username="admin", password="secret"))
            await session.flush()

            star = (await session.exec(
                sm_select(Permission).where(Permission.codename == "*")
            )).first()
            super_role = Role(name="Super Admin")
            session.add(super_role)
            await session.flush()
            if star:
                session.add(RolePermission(role_id=super_role.id, permission_id=star.id))
            admin_user = (await session.exec(sm_select(AdminUser))).first()
            session.add(UserRole(user_id=str(admin_user.id), role_id=super_role.id))
            await session.commit()

    yield


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(lifespan=_lifespan)
app.mount("/admin", panel.build())

@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/admin")
