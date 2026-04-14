# adminpanel

A declarative admin panel framework for FastAPI. Define your resources once
in Python — get a full admin UI with tables, forms, search, sorting, and
dashboards. No HTML, no JS, no separate frontend process.

## Installation

```bash
pip install adminpanel
```

Or from source:

```bash
git clone https://github.com/yourname/adminpanel
cd adminpanel
pip install -e .
```

## Drop-in usage

Add three lines to your existing FastAPI project:

```python
from fastapi import FastAPI
from adminpanel import AdminPanel, Resource

app = FastAPI()          # your existing app — unchanged

# 1. Define a resource
class UserResource(Resource):
    label = "User"
    label_plural = "Users"

    async def get_list(self, *, page, per_page, search, **kwargs):
        users = await user_service.list(page=page, search=search)
        return {"records": users, "total": users.total}

    async def get_record(self, id):
        return await user_service.get(id)

    async def save_record(self, id, data):
        if id is None:
            return await user_service.create(data)
        return await user_service.update(id, data)

    async def delete_record(self, id):
        await user_service.delete(id)

# 2. Create the panel
panel = AdminPanel(
    title="My App",
    prefix="/admin",          # default, change to anything
    brand_color="#6366f1",    # your brand colour
)

# 3. Register resources and mount
panel.register(UserResource)
panel.mount(app)              # attaches to your existing FastAPI app
```

Open `http://localhost:8000/admin` — done.

AdminPanel **never** touches your existing routes, middleware, OpenAPI
docs, or dependency injection setup. All admin routes are excluded from
your OpenAPI schema by default.

## Resource data hooks

Override these methods to connect your service or ORM layer:

| Method | When called | Must return |
|---|---|---|
| `get_list(page, per_page, search, sort_by, sort_dir, filters)` | List page load & search | `{"records": [...], "total": int}` |
| `get_record(id)` | Edit page load | single record (dict or model) |
| `save_record(id, data)` | Form submit (id=None for create) | saved record |
| `delete_record(id)` | Delete action | None |

Records can be plain `dict`s or any ORM model instance (SQLModel,
SQLAlchemy, dataclass). The template layer handles both transparently.

## Declaring columns and fields

```python
from example_app.helpers import Col, Field   # Phase 3 will ship typed classes

class OrderResource(Resource):
    label = "Order"
    label_plural = "Orders"

    table_columns = [
        Col("order_number", "Order #", sortable=True),
        Col("customer",     "Customer"),
        Col("status",       "Status"),
        Col("total",        "Total"),
    ]

    form_fields = [
        Field("order_number", required=True),
        Field("status", field_type="select",
              options=["pending", "processing", "shipped", "delivered"]),
        Field("notes", field_type="textarea"),
    ]
```

## Configuration

```python
AdminPanel(
    title="Acme Admin",       # shown in sidebar header and browser tab
    prefix="/admin",          # URL prefix for all admin routes
    brand_color="#6366f1",    # hex colour for sidebar and buttons
    logo_url="/static/logo.png",  # optional logo, replaces text title
)
```

## Running the example app

```bash
git clone https://github.com/yourname/adminpanel
cd adminpanel
pip install -e .
uvicorn example_app.main:app --reload
# open http://localhost:8000/admin
```

## What's coming

- **Phase 2** — Typed column and field classes (`columns.Badge`, `fields.Select`, etc.)
- **Phase 3** — HTMX live search, sort, and pagination without page reloads
- **Phase 4** — Action system: row actions, bulk actions, confirm modals
- **Phase 5** — Dashboard widgets: stat cards, line charts, pie charts
- **Phase 6** — Auth and role-based access control
