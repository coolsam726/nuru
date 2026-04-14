"""
Example app: two independent admin panels on the same FastAPI app.

Run with:  uvicorn example_app.main:app --reload

  /admin  — auth-protected (user: admin / pass: secret)
  /ops    — open (in-memory servers)
  /db     — SQLModel Product demo
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from sqlmodel import SQLModel, Field as SMField, select as sm_select
from sqlmodel.ext.asyncio.session import AsyncSession as _AsyncSession
from sqlalchemy.ext.asyncio import (
    create_async_engine as _cae,
    async_sessionmaker as _asm,
)

from nuru import AdminPanel, Resource, SimpleAuthBackend, columns, fields
from nuru.actions import Action


@asynccontextmanager
async def _lifespan(app: FastAPI):
    from nuru.migrations import sync_schema

    await sync_schema(_engine, SQLModel.metadata)

    async with _get_session() as session:
        if not (await session.exec(sm_select(User))).first():
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


app = FastAPI(title="Example App", lifespan=_lifespan)

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
# In-memory servers (ops panel only)
# ---------------------------------------------------------------------------

_servers = [
    {
        "id": 1,
        "hostname": "web-01",
        "region": "eu-west",
        "status": "healthy",
        "cpu": 23,
    },
    {
        "id": 2,
        "hostname": "web-02",
        "region": "eu-west",
        "status": "healthy",
        "cpu": 41,
    },
    {"id": 3, "hostname": "db-01", "region": "us-east", "status": "warning", "cpu": 87},
    {
        "id": 4,
        "hostname": "cache-01",
        "region": "us-east",
        "status": "healthy",
        "cpu": 12,
    },
]

# ---------------------------------------------------------------------------
# /admin  —  UserResource
# ---------------------------------------------------------------------------


class UserResource(Resource):
    label = "User"
    label_plural = "Users"
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
# /ops  —  ServerResource (in-memory)
# ---------------------------------------------------------------------------


class ServerResource(Resource):
    label = "Server"
    label_plural = "Servers"

    table_columns = [
        columns.Text("hostname", "Hostname", sortable=True),
        columns.Text("region", "Region", sortable=True),
        columns.Badge(
            "status",
            "Status",
            colors={
                "healthy": "green",
                "warning": "amber",
                "critical": "red",
            },
        ),
        columns.Text("cpu", "CPU %"),
    ]

    form_fields = [
        fields.Text("hostname", "Hostname", required=True),
        fields.Select("region", "Region", options=["eu-west", "us-east", "ap-south"]),
        fields.Select("status", "Status", options=["healthy", "warning", "critical"]),
        fields.Number("cpu", "CPU %"),
    ]

    async def get_list(
        self,
        *,
        page=1,
        per_page=25,
        search=None,
        sort_by=None,
        sort_dir="asc",
        filters=None,
    ):
        data = list(_servers)
        if search:
            q = search.lower()
            data = [s for s in data if q in s["hostname"].lower()]
        if sort_by and sort_by in ("hostname", "region"):
            data.sort(key=lambda s: s.get(sort_by, ""), reverse=(sort_dir == "desc"))
        start = (page - 1) * per_page
        return {"records": data[start : start + per_page], "total": len(data)}

    async def get_record(self, id):
        return next((s for s in _servers if str(s["id"]) == str(id)), None)

    async def save_record(self, id, data):
        if id is None:
            new_id = max(s["id"] for s in _servers) + 1
            record = {"id": new_id, **data}
            _servers.append(record)
            return record
        for s in _servers:
            if str(s["id"]) == str(id):
                s.update(data)
                return s

    async def delete_record(self, id):
        _servers[:] = [s for s in _servers if str(s["id"]) != str(id)]


# ---------------------------------------------------------------------------
# /db  —  ProductResource (SQLModel)
# ---------------------------------------------------------------------------


class ProductResource(Resource):
    label = "Product"
    label_plural = "Products"
    model = Product
    session_factory = _get_session
    search_fields = ["name", "sku"]
    can_delete = True

    table_columns = [
        columns.Text("name", "Name", sortable=True),
        columns.Text("sku", "SKU", sortable=True),
        columns.Currency("price", "Price", currency="USD"),
        columns.Boolean("in_stock", "In Stock"),
        columns.Currency("stock_quantity", "Stock Qty", currency=""),
    ]

    row_actions = [
        Action(
            "restock",
            label="Restock",
            handler="restock_product",
            style="success",
            icon="M12 4v16m8-8H4",
            form_fields=[
                fields.Number("quantity", "Quantity to add", required=True),
            ],
        ),
    ]

    async def restock_product(self, record_id, data, request):
        qty = int(data.get("quantity") or 0)
        if qty <= 0:
            raise ValueError("Quantity must be positive")
        async with _get_session() as session:
            record = await session.get(Product, int(record_id))
            if record is None:
                raise ValueError(f"Product {record_id} not found")
            record.stock_quantity = (record.stock_quantity or 0) + qty
            record.in_stock = True
            session.add(record)
            await session.commit()


# ---------------------------------------------------------------------------
# Panel mounts
# ---------------------------------------------------------------------------

admin_panel = AdminPanel(
    title="Acme Admin",
    prefix="/admin",
    brand_color="rgb(227 160 8)",
    per_page=5,
    auth=SimpleAuthBackend(
        username="admin",
        password="secret",
        secret_key="dev-secret-key-change-in-production",
    ),
)
admin_panel.register(UserResource)
admin_panel.register(OrderResource)
admin_panel.mount(app)

ops_panel = AdminPanel(title="Ops", prefix="/ops", brand_color="#e11d48")
ops_panel.register(ServerResource)
ops_panel.mount(app)

db_panel = AdminPanel(title="DB Panel", prefix="/db", brand_color="#0f766e")
db_panel.register(ProductResource)
db_panel.mount(app)


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
