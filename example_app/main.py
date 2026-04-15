"""
Example app: two independent admin panels on the same FastAPI app.

Run with:  uvicorn example_app.main:app --reload

  /admin  — auth-protected (user: admin / pass: secret)
  /ops    — open (in-memory servers)
  /db     — SQLModel Product demo
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from sqlmodel import SQLModel, Field as SMField, select as sm_select
from sqlmodel.ext.asyncio.session import AsyncSession as _AsyncSession
from sqlalchemy.ext.asyncio import (
    create_async_engine as _cae,
    async_sessionmaker as _asm,
)

import nuru.roles  # registers Permission, Role, RolePermission, UserRole with SQLModel.metadata
from nuru import (
    AdminPanel, Page, Resource,
    SimpleAuthBackend, DatabaseAuthBackend,
    db_permission_checker,
    Permission, Role, RolePermission, UserRole,
    columns, fields,
)
from nuru.actions import Action


@asynccontextmanager
async def _lifespan(app: FastAPI):
    from nuru.migrations import sync_schema

    # Creates both application tables AND nuru_permission / nuru_role / etc.
    await sync_schema(_engine, SQLModel.metadata)
    # Upsert permission rows for every registered resource.
    await admin_panel.sync_permissions(_get_session)

    # ── Seed roles, permissions, and admin users ───────────────────────────
    async with _get_session() as session:
        if not (await session.exec(sm_select(Role))).first():
            # 1. Create roles.
            super_admin = Role(name="Super Admin", description="Full system access")
            editor      = Role(name="Content Editor", description="Can create and edit content")
            read_only   = Role(name="Read Only",      description="View-only access")
            session.add_all([super_admin, editor, read_only])
            await session.flush()

            # 2. Assign permissions to roles.
            star_perm = (await session.exec(
                sm_select(Permission).where(Permission.codename == "*")
            )).first()
            if star_perm:
                session.add(RolePermission(role_id=super_admin.id, permission_id=star_perm.id))

            editor_codenames = [
                "user:list", "user:view", "user:create", "user:edit",
                "order:list", "order:view", "order:create", "order:edit",
                "user:action", "order:action",
            ]
            editor_perms = (await session.exec(
                sm_select(Permission).where(Permission.codename.in_(editor_codenames))
            )).all()
            for p in editor_perms:
                session.add(RolePermission(role_id=editor.id, permission_id=p.id))

            viewer_codenames = [
                "user:list", "user:view",
                "order:list", "order:view",
            ]
            viewer_perms = (await session.exec(
                sm_select(Permission).where(Permission.codename.in_(viewer_codenames))
            )).all()
            for p in viewer_perms:
                session.add(RolePermission(role_id=read_only.id, permission_id=p.id))

            await session.commit()

    # ── Seed demo admin users (if table is empty) ────────────────────────
    async with _get_session() as session:
        if not (await session.exec(sm_select(User))).first():
            # Two panel login accounts (plaintext passwords — dev only!).
            admin_user  = User(name="Admin User",  email="admin@acme.com",  password="secret",    role="admin",  active=True)
            viewer_user = User(name="Viewer User", email="viewer@acme.com", password="viewer123", role="viewer", active=True)
            session.add_all([admin_user, viewer_user])
            await session.flush()

            # Assign admin_user → Super Admin role, viewer_user → Read Only.
            super_admin = (await session.exec(
                sm_select(Role).where(Role.name == "Super Admin")
            )).first()
            read_only = (await session.exec(
                sm_select(Role).where(Role.name == "Read Only")
            )).first()
            if super_admin:
                session.add(UserRole(user_id=str(admin_user.id), role_id=super_admin.id))
            if read_only:
                session.add(UserRole(user_id=str(viewer_user.id), role_id=read_only.id))

            session.add_all(
                [
                    User(
                        name="Alice Kamau",
                        email="alice@example.com",
                        role="admin",
                        active=True,
                    ),
                    User(
                        name="Bob Mwangi",
                        email="bob@example.com",
                        role="editor",
                        active=True,
                    ),
                    User(
                        name="Carol Ochieng",
                        email="carol@example.com",
                        role="viewer",
                        active=False,
                    ),
                    User(
                        name="David Otieno",
                        email="david@example.com",
                        role="editor",
                        active=True,
                    ),
                    # Seed more users to demonstrate pagination and search:
                    User(
                        name="Eve Njeri",
                        email="eve@example.com",
                        role="viewer",
                        active=True,
                    ),
                    User(
                        name="Frank Oduor",
                        email="frank@example.com",
                        role="viewer",
                        active=True,
                    ),
                    User(
                        name="Grace Achieng",
                        email="grace@example.com",
                        role="viewer",
                        active=True,
                    ),
                    User(
                        name="Heidi Onyango",
                        email="heidi@example.com",
                        role="editor",
                        active=False,
                    ),
                    User(
                        name="Ivan Otieno",
                        email="ivan@example.com",
                        role="viewer",
                        active=True,
                    ),
                    User(
                        name="Judy Wanjiku",
                        email="judy@example.com",
                        role="admin",
                        active=True,
                    ),
                    User(
                        name="Karl Mwangi",
                        email="karl@example.com",
                        role="viewer",
                        active=True,
                    ),
                    User(
                        name="Leo Kamau",
                        email="leo@example.com",
                        role="viewer",
                        active=True,
                    ),
                ]
            )

        if not (await session.exec(sm_select(Order))).first():
            session.add_all(
                [
                    Order(
                        order_number="ORD-001",
                        customer="Alice Kamau",
                        status="delivered",
                        total=4500.00,
                    ),
                    Order(
                        order_number="ORD-002",
                        customer="Bob Mwangi",
                        status="shipped",
                        total=1200.50,
                    ),
                    Order(
                        order_number="ORD-003",
                        customer="Carol Ochieng",
                        status="pending",
                        total=890.00,
                    ),
                    Order(
                        order_number="ORD-004",
                        customer="David Otieno",
                        status="processing",
                        total=3300.75,
                    ),
                    Order(
                        order_number="ORD-005",
                        customer="Eve Njeri",
                        status="cancelled",
                        total=150.00,
                    ),
                    Order(
                        order_number="ORD-006",
                        customer="Frank Oduor",
                        status="pending",
                        total=2200.00,
                    ),
                    Order(
                        order_number="ORD-007",
                        customer="Grace Achieng",
                        status="pending",
                        total=780.00,
                    ),
                    Order(
                        order_number="ORD-008",
                        customer="Heidi Onyango",
                        status="processing",
                        total=4100.00,
                    ),
                    Order(
                        order_number="ORD-009",
                        customer="Ivan Otieno",
                        status="shipped",
                        total=670.25,
                    ),
                    Order(
                        order_number="ORD-010",
                        customer="Judy Wanjiku",
                        status="delivered",
                        total=540.00,
                    ),
                    Order(
                        order_number="ORD-011",
                        customer="Karl Mwangi",
                        status="pending",
                        total=1300.00,
                    ),
                    Order(
                        order_number="ORD-012",
                        customer="Leo Kamau",
                        status="cancelled",
                        total=250.00,
                    ),
                    Order(
                        order_number="ORD-013",
                        customer="Alice Kamau",
                        status="processing",
                        total=900.00,
                    ),
                    # Populate 50 more records to demonstrate pagination:
                    *[
                        Order(
                            order_number=f"ORD-{100+i:03d}",
                            customer="Customer " + str(i),
                            status="pending",
                            total=100.00 + i * 10,
                        )
                        for i in range(1, 51)
                    ],
                ]
            )

        await session.commit()

    yield


app = FastAPI(title="Nuru Demo App", lifespan=_lifespan)

# ---------------------------------------------------------------------------
# Shared async SQLite engine
# ---------------------------------------------------------------------------

_engine = _cae("sqlite+aiosqlite:///example_db.sqlite3")
_SessionFactory = _asm(_engine, class_=_AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def _get_session():
    async with _SessionFactory() as session:
        yield session


# ---------------------------------------------------------------------------
# SQLModel table definitions
# ---------------------------------------------------------------------------


class User(SQLModel, table=True):
    __tablename__ = "user"
    id: Optional[int] = SMField(default=None, primary_key=True)
    name: str
    email: str
    password: Optional[str] = None  # plaintext for demo; hash with bcrypt in production
    role: str = "viewer"
    active: bool = True

    def __str__(self) -> str:
        return self.name


class Order(SQLModel, table=True):
    __tablename__ = "order"
    id: Optional[int] = SMField(default=None, primary_key=True)
    order_number: str
    customer: str
    status: str = "pending"
    total: float = 0.0
    notes: Optional[str] = None

    def __str__(self) -> str:
        return self.order_number


class Product(SQLModel, table=True):
    __tablename__ = "product"
    id: Optional[int] = SMField(default=None, primary_key=True)
    name: str
    sku: str
    price: float
    in_stock: bool = True
    stock_quantity: float = 0

    def __str__(self) -> str:
        return f"{self.name} ({self.sku})"


# ---------------------------------------------------------------------------
# /admin  —  UserResource
# ---------------------------------------------------------------------------


class UserResource(Resource):
    label = "User"
    label_plural = "Users"
    nav_sort = 30
    nav_label = "Manage Users"
    nav_icon = "user"
    model = User
    session_factory = _get_session
    search_fields = ["name", "email"]
    form_cols = 2

    row_actions = [
        Action(
            "activate",
            label="Activate",
            handler="activate_user",
            style="success",
            icon="M5 13l4 4L19 7",
        ),
        Action(
            "deactivate",
            label="Deactivate",
            handler="deactivate_user",
            style="warning",
            confirm="Deactivate this user?",
            icon="M6 18L18 6M6 6l12 12",
        ),
        Action(
            "reset_email",
            label="Reset email",
            handler="reset_email",
            style="default",
            form_fields=[
                fields.Email(
                    "new_email",
                    "New email address",
                    required=True,
                    placeholder="user@example.com",
                ),
            ],
        ),
    ]

    list_actions = [
        Action(
            "export_csv",
            label="Export CSV",
            handler="export_csv",
            style="secondary",
            icon="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4",
        ),
        Action(
            "send_notice",
            label="Send Notice",
            handler="send_notice",
            style="warning",
            form_fields=[
                fields.Text("subject", "Subject", required=True),
                fields.Textarea(
                    "body", "Message", required=True, placeholder="Enter notice text..."
                ),
            ],
        ),
    ]

    table_columns = [
        columns.Text("name", "Name", sortable=True),
        columns.Text("email", "Email", sortable=True),
        columns.Badge(
            "role",
            "Role",
            colors={
                "admin": "purple",
                "editor": "blue",
                "viewer": "gray",
            },
        ),
        columns.Boolean("active", "Active"),
    ]
    detail_fields = [
        fields.Fieldset(
            fields=[
                fields.Text("name", "Full name"),
                fields.Email("email", "Email address"),
                fields.Select("role", "Role", options=["admin", "editor", "viewer"]),
            ],
            title="User Details",
            description="Basic information about the user.",
            cols=2,
        )
    ]
    form_fields = [
        fields.Section(
            col_span="full",
            cols=2,
            fields=[
                fields.Text("name", "Full name", required=True, placeholder="Jane Doe"),
                fields.Email("email", "Email", required=True),
                fields.Select("role", "Role", options=["admin", "editor", "viewer"]),
                fields.Checkbox("active", "Active", help_text="Uncheck to deactivate"),
            ],
        )
    ]

    # Action handlers

    async def _set_active(self, record_id, value: bool):
        async with _get_session() as session:
            user = await session.get(User, int(record_id))
            if user is None:
                raise ValueError(f"User {record_id} not found")
            user.active = value
            session.add(user)
            await session.commit()

    async def activate_user(self, record_id, data, request):
        await self._set_active(record_id, True)

    async def deactivate_user(self, record_id, data, request):
        await self._set_active(record_id, False)

    async def reset_email(self, record_id, data, request):
        new_email = data.get("new_email", "").strip()
        if not new_email:
            raise ValueError("Email address is required")
        async with _get_session() as session:
            user = await session.get(User, int(record_id))
            if user is None:
                raise ValueError(f"User {record_id} not found")
            user.email = new_email
            session.add(user)
            await session.commit()

    async def export_csv(self, record_id, data, request):
        async with _get_session() as session:
            users = (await session.exec(sm_select(User))).all()
        lines = ["id,name,email,role,active"]
        for u in users:
            lines.append(f"{u.id},{u.name},{u.email},{u.role},{u.active}")
        return PlainTextResponse(
            "\n".join(lines),
            headers={"Content-Disposition": "attachment; filename=users.csv"},
        )

    async def send_notice(self, record_id, data, request):
        subject = data.get("subject", "")
        body = data.get("body", "")
        print(f"[NOTICE] Subject={subject!r}  Body={body!r}")


# ---------------------------------------------------------------------------
# /admin  —  OrderResource
# ---------------------------------------------------------------------------


class OrderResource(Resource):
    label = "Order"
    label_plural = "Orders"
    nav_sort = 10
    nav_icon = "briefcase"
    model = Order
    session_factory = _get_session
    search_fields = ["order_number", "customer"]
    form_cols = 2

    table_columns = [
        columns.Text("order_number", "Order #", sortable=True),
        columns.Text("customer", "Customer", sortable=True),
        columns.Badge(
            "status",
            "Status",
            colors={
                "pending": "amber",
                "processing": "blue",
                "shipped": "purple",
                "delivered": "green",
                "cancelled": "red",
            },
        ),
        columns.Currency("total", "Total", currency="KES"),
    ]

    form_fields = [
        fields.Section(
            title="Order Details",
            cols=2,
            col_span="full",
            fields=[
                fields.Text("order_number", "Order number", required=True),
                fields.Text("customer", "Customer", required=True),
                fields.Select(
                    "status",
                    "Status",
                    options=[
                        "pending",
                        "processing",
                        "shipped",
                        "delivered",
                        "cancelled",
                    ],
                ),
                fields.Number("total", "Total (KES)"),
            ],
        ),
        fields.Section(
            title="Internal Notes",
            col_span="full",
            fields=[
                fields.Textarea(
                    "notes",
                    "Internal notes",
                    placeholder="Staff-only notes about this order...",
                ),
            ],
        ),
    ]

    form_actions = [
        Action(
            "mark_shipped",
            label="Mark as Shipped",
            handler="mark_shipped",
            placement="header",
            style="primary",
            confirm="Mark this order as shipped?",
        ),
        Action(
            "cancel_order",
            label="Cancel Order",
            handler="cancel_order",
            placement="header",
            style="danger",
            form_fields=[
                fields.Textarea(
                    "reason",
                    "Cancellation reason",
                    required=True,
                    placeholder="Explain why this order is being cancelled...",
                ),
            ],
        ),
        Action(
            "add_note",
            label="Add Note",
            handler="add_note",
            placement="inline",
            style="default",
            form_fields=[
                fields.Textarea(
                    "note",
                    "Internal note",
                    required=True,
                    placeholder="Visible to staff only...",
                ),
            ],
        ),
    ]

    # Action handlers

    async def mark_shipped(self, record_id, data, request):
        async with _get_session() as session:
            order = await session.get(Order, int(record_id))
            if order is None:
                raise ValueError(f"Order {record_id} not found")
            order.status = "shipped"
            session.add(order)
            await session.commit()

    async def cancel_order(self, record_id, data, request):
        reason = data.get("reason", "").strip()
        async with _get_session() as session:
            order = await session.get(Order, int(record_id))
            if order is None:
                raise ValueError(f"Order {record_id} not found")
            order.status = "cancelled"
            if reason:
                existing = order.notes or ""
                order.notes = f"[CANCELLED] {reason}\n{existing}".strip()
            session.add(order)
            await session.commit()

    async def add_note(self, record_id, data, request):
        note = data.get("note", "").strip()
        if not note:
            return
        async with _get_session() as session:
            order = await session.get(Order, int(record_id))
            if order is None:
                raise ValueError(f"Order {record_id} not found")
            existing = order.notes or ""
            order.notes = f"{existing}\n{note}".strip()
            session.add(order)
            await session.commit()


# ---------------------------------------------------------------------------
# Custom Page: Reports
# ---------------------------------------------------------------------------

_EXAMPLE_TEMPLATES = Path(__file__).parent / "templates"

# In-memory store for the quick-note demo form
_quick_notes: list[dict] = []


class ReportsPage(Page):
    """Live summary page — showcases Page, form_widget, table_widget, detail_grid."""

    label = "Reports"
    slug = "reports"
    nav_sort = 20
    nav_icon = "chart-bar"

    async def get_context(self, request: Request) -> dict:
        async with _get_session() as session:
            all_users = (await session.exec(sm_select(User))).all()
            all_orders = (await session.exec(sm_select(Order))).all()

        total_users = len(all_users)
        active_users = sum(1 for u in all_users if u.active)
        total_orders = len(all_orders)
        total_revenue = sum(o.total for o in all_orders)
        avg_order = total_revenue / total_orders if total_orders else 0
        pending_orders = sum(1 for o in all_orders if o.status == "pending")

        role_counts = {
            r: sum(1 for u in all_users if u.role == r)
            for r in ("admin", "editor", "viewer")
        }

        recent_orders = sorted(all_orders, key=lambda o: o.id or 0, reverse=True)[:8]

        # ── KPI detail grid ──────────────────────────────────────────────
        kpi_fields = [
            fields.Text("total_users", "Total users"),
            fields.Text("active_users", "Active users"),
            fields.Text("total_orders", "Total orders"),
            fields.Text("pending_orders", "Pending orders"),
            fields.Text("total_revenue", "Total revenue (KES)"),
            fields.Text("avg_order", "Avg order value (KES)"),
        ]
        kpi = {
            "total_users": str(total_users),
            "active_users": f"{active_users} ({100 * active_users // total_users if total_users else 0}%)",
            "total_orders": str(total_orders),
            "pending_orders": str(pending_orders),
            "total_revenue": f"{total_revenue:,.2f}",
            "avg_order": f"{avg_order:,.2f}",
        }

        # ── Role breakdown Fieldset ──────────────────────────────────────
        role_fields = [
            fields.Fieldset(
                title="Roles",
                description="Count of users by assigned role.",
                cols=3,
                col_span="full",
                fields=[
                    fields.Text("admin", "Admins"),
                    fields.Text("editor", "Editors"),
                    fields.Text("viewer", "Viewers"),
                ],
            )
        ]

        # ── table_widget: recent orders ───────────────────────────────────
        order_columns = [
            columns.Text("order_number", "Order #"),
            columns.Text("customer", "Customer"),
            columns.Badge(
                "status",
                "Status",
                colors={
                    "pending": "amber",
                    "processing": "blue",
                    "shipped": "purple",
                    "delivered": "green",
                    "cancelled": "red",
                },
            ),
            columns.Currency("total", "Total (KES)", currency="KES"),
        ]

        # ── form_widget: quick note ───────────────────────────────────────
        note_fields = [
            fields.Text("author", "Your name", required=True, placeholder="Jane Doe"),
            fields.Textarea(
                "message",
                "Note",
                required=True,
                placeholder="Write a quick note visible to other admins...",
                col_span="full",
            ),
        ]

        # ── table_widget: submitted notes ────────────────────────────────
        note_columns = [
            columns.Text("author", "Author"),
            columns.Text("message", "Message"),
            columns.Text("posted_at", "Posted"),
        ]

        error = request.query_params.get("error", "")
        success = request.query_params.get("success", "")

        return {
            "kpi_fields": kpi_fields,
            "kpi": kpi,
            "role_fields": role_fields,
            "role_counts": {k: str(v) for k, v in role_counts.items()},
            "order_columns": order_columns,
            "recent_orders": recent_orders,
            "note_fields": note_fields,
            "note_columns": note_columns,
            "notes": list(_quick_notes),
            "form_error": error,
            "form_success": success,
            # form_widget needs these
            "record": None,
            "errors": None,
        }

    async def handle_post(self, request: Request) -> Response:
        form = await request.form()
        author = str(form.get("author", "")).strip()
        message = str(form.get("message", "")).strip()

        if not author or not message:
            return RedirectResponse(
                f"{self.panel.prefix}/{self.slug}?error=Please+fill+in+all+fields.",
                status_code=303,
            )

        from datetime import datetime, timezone

        _quick_notes.insert(
            0,
            {
                "author": author,
                "message": message,
                "posted_at": datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC"),
            },
        )
        return RedirectResponse(
            f"{self.panel.prefix}/{self.slug}?success=Note+posted.",
            status_code=303,
        )


# ---------------------------------------------------------------------------
# Panel mounts
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Role management resource
# ---------------------------------------------------------------------------


class _RoleView:
    """Thin wrapper returned by RoleResource.get_record for the detail page.

    Mirrors all Role attributes and adds ``permissions_list`` — a sorted,
    comma-separated string of codenames assigned to the role — so it can be
    displayed as a read-only field without any framework changes.
    """

    def __init__(self, role: Role, codenames: list[str]) -> None:
        self.id          = role.id
        self.name        = role.name
        self.description = role.description
        self.permissions_list = ", ".join(sorted(codenames)) if codenames else "—"

    def __str__(self) -> str:
        return self.name


class RoleResource(Resource):
    """Manage nuru roles from the admin panel."""

    label = "Role"
    label_plural = "Roles"
    nav_sort = 50
    nav_icon = "shield-check"
    model = Role
    session_factory = _get_session
    search_fields = ["name", "description"]

    table_columns = [
        columns.Text("name", "Role Name", sortable=True),
        columns.Text("description", "Description"),
    ]
    form_fields = [
        fields.Section(
            title="Role Details",
            cols=2,
            col_span="full",
            fields=[
                fields.Text("name", "Role Name", required=True, placeholder="e.g. Content Editor"),
                fields.Text("description", "Description", placeholder="What this role can do"),
            ],
        )
    ]
    detail_fields = [
        fields.Fieldset(
            title="Role Details",
            cols=2,
            fields=[
                fields.Text("name", "Role Name"),
                fields.Text("description", "Description"),
            ],
        ),
        fields.Fieldset(
            title="Assigned Permissions",
            description="Codenames granted to users in this role.",
            col_span="full",
            cols=1,
            fields=[
                fields.Text("permissions_list", "Permissions"),
            ],
        ),
    ]

    async def get_record(self, id: Any) -> _RoleView | None:
        async with _get_session() as session:
            role = await session.get(Role, int(id))
            if role is None:
                return None
            role_perms = (await session.exec(
                sm_select(RolePermission).where(RolePermission.role_id == role.id)
            )).all()
            perm_ids = [rp.permission_id for rp in role_perms]
            codenames: list[str] = []
            if perm_ids:
                perms = (await session.exec(
                    sm_select(Permission).where(Permission.id.in_(perm_ids))
                )).all()
                codenames = [p.codename for p in perms]
            return _RoleView(role, codenames)


# ---------------------------------------------------------------------------
# Panel mounts
# ---------------------------------------------------------------------------

admin_panel = AdminPanel(
    title="Acme Admin",
    prefix="/admin",
    per_page=10,
    # DatabaseAuthBackend: looks up users from DB, loads role-based permissions.
    # Login: admin@acme.com / secret  (Super Admin — full access)
    #        viewer@acme.com / viewer123  (Read Only — list & view only)
    auth=DatabaseAuthBackend(
        user_model=User,
        session_factory=_get_session,
        username_field="email",
        password_field="password",
        # No verify_password → plain-text compare via hmac.compare_digest (dev only).
        # In production: verify_password=passlib_ctx.verify
        secret_key="dev-secret-key-change-in-production",
        extra_fields=["name", "role"],
    ),
    permission_checker=db_permission_checker,
    template_dirs=[_EXAMPLE_TEMPLATES],
)
admin_panel.register(UserResource)
admin_panel.register(OrderResource)
admin_panel.register(RoleResource)
admin_panel.register_page(ReportsPage)
admin_panel.mount(app)

# ---------------------------------------------------------------------------
# Role management resource (staff-facing CRUD for nuru_role)
# ---------------------------------------------------------------------------
# (registered with admin_panel above)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------


@app.get("/")
async def root():
    return {
        "panels": {
            "admin (auth-protected)": "/admin  (user: admin / pass: secret)",
            "ops   (open)": "/ops",
            "db    (SQLModel demo)": "/db",
        }
    }
