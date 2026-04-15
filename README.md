# Nuru
[![CI](https://github.com/coolsam726/nuru/actions/workflows/python-tests.yml/badge.svg)](https://github.com/coolsam726/nuru/actions)
[![Python versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org)
[![PyPI version](https://img.shields.io/pypi/v/nuru.svg)](https://pypi.org/project/nuru)

A declarative admin panel framework for FastAPI. Define your resources once
in Python — get a full admin UI with tables, forms, search, sorting, and
dashboards. No HTML, no JS, no separate frontend process.

![screenshot](image.png)

## Installation

```bash
pip install nuru
```

Or from source:

```bash
git clone https://github.com/yourname/nuru
cd nuru
pip install -e .
```

## Drop-in usage

Add three lines to your existing FastAPI project:

```python
from fastapi import FastAPI
from nuru import AdminPanel, Resource

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

Nuru **never** touches your existing routes, middleware, OpenAPI
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
from nuru import columns, fields

class OrderResource(Resource):
    label = "Order"
    label_plural = "Orders"

    table_columns = [
        columns.Text("order_number", "Order #", sortable=True),
        columns.Text("customer", "Customer"),
        columns.Badge("status", "Status", colors={
            "pending": "amber", "shipped": "blue", "delivered": "green",
        }),
        columns.Currency("total", "Total", currency="USD"),
    ]

    form_fields = [
        fields.Text("order_number", required=True),
        fields.Select("status", options=["pending", "processing", "shipped", "delivered"]),
        fields.Textarea("notes"),
    ]
```

## Actions

```python
from nuru import actions, fields

class OrderResource(Resource):
    row_actions = [
        actions.Action(
            key="mark_shipped",
            label="Mark Shipped",
            style="primary",
            confirm="Mark this order as shipped?",
            handler="handle_mark_shipped",
        ),
    ]

    form_actions = [
        actions.Action(
            key="add_note",
            label="Add Note",
            placement="inline",
            form_fields=[fields.Textarea("note", label="Note", required=True)],
            handler="handle_add_note",
        ),
    ]

    async def handle_mark_shipped(self, record_id, data, request):
        # update the record, return optional redirect URL
        ...

    async def handle_add_note(self, record_id, data, request):
        note = data.get("note")
        ...
```

## SQLModel integration

Set `model` and `session_factory` for zero-boilerplate CRUD — columns and
fields are auto-generated from model annotations:

```python
from nuru import AdminPanel, Resource
from nuru.migrations import sync_schema

class UserResource(Resource):
    label = "User"
    label_plural = "Users"
    model = User                    # your SQLModel class
    session_factory = get_session   # async context-manager factory
    search_fields = ["name", "email"]
```

## Authentication

### Simple (single-user)

```python
from nuru import AdminPanel
from nuru.auth import SimpleAuthBackend

panel = AdminPanel(
    title="My App",
    prefix="/admin",
    auth=SimpleAuthBackend(
        username="admin",
        password="secret",
        secret_key="change-me-in-production",
    ),
)
```

`SimpleAuthBackend` signs a session cookie with `itsdangerous`. Because there is only one user with no `_permissions` key, the built-in `default_permission_checker` grants **full access** — no permission setup required.

---

## Roles & Permissions

Nuru includes a Spatie-style Role/Permission system for multi-user panels.

### How it works

| Concept | Description |
|---|---|
| **Permission** | Fixed codename scoped to a resource+action, e.g. `users:list`, `orders:delete` |
| **Role** | User-defined group of permissions (many-to-many) |
| **UserRole** | Which roles a user holds (many-to-many, user identified by `str(pk)`) |

At runtime, nuru checks **permissions** — not role names, which can change freely.

### Codename format

`{resource_slug}:{action}` — e.g.:

| Codename | Meaning |
|---|---|
| `users:list` | Browse the Users list page |
| `users:create` | Create a new User |
| `users:edit` | Edit an existing User |
| `users:view` | View User detail |
| `users:delete` | Delete a User |
| `users:action` | Run any row/list action on Users |
| `users:action:export_csv` | Run the specific `export_csv` action only |
| `users:*` | All actions on Users |
| `*` | Superuser — everything |

### Setup

```python
import nuru.roles  # registers the 4 nuru_* tables with SQLModel.metadata
from nuru import AdminPanel, DatabaseAuthBackend, db_permission_checker
from passlib.context import CryptContext

_pwd = CryptContext(schemes=["bcrypt"])

panel = AdminPanel(
    title="My App",
    prefix="/admin",
    auth=DatabaseAuthBackend(
        user_model=User,
        session_factory=get_session,
        username_field="email",
        password_field="password",
        verify_password=_pwd.verify,   # omit for plaintext (dev only)
        secret_key="change-me-in-production",
        extra_fields=["name"],         # extra User fields to expose in templates
    ),
    permission_checker=db_permission_checker,
)
```

At startup, sync the schema **and** upsert permission rows:

```python
from nuru.migrations import sync_schema

@app.on_event("startup")
async def on_startup():
    await sync_schema(engine, SQLModel.metadata)   # creates nuru_* tables too
    await panel.sync_permissions(get_session)      # upserts permission codenames
```

### Seeding roles programmatically

```python
from nuru.roles import Permission, Role, RolePermission, UserRole

async def seed_roles(session):
    admin_role = Role(name="Super Admin", description="Full access")
    viewer_role = Role(name="Read Only",  description="View only")
    session.add_all([admin_role, viewer_role])
    await session.flush()

    star = (await session.exec(select(Permission).where(Permission.codename == "*"))).first()
    session.add(RolePermission(role_id=admin_role.id, permission_id=star.id))

    view_perms = (await session.exec(
        select(Permission).where(Permission.codename.in_(["users:list", "users:view"]))
    )).all()
    for p in view_perms:
        session.add(RolePermission(role_id=viewer_role.id, permission_id=p.id))

    # Assign a role to a user
    session.add(UserRole(user_id=str(user.id), role_id=admin_role.id))
    await session.commit()
```

### Custom permission checker

Pass any `(user, codename, resource) -> bool` callable (sync or async) to override the built-in logic:

```python
async def my_checker(user, codename, resource):
    if user is None:
        return False
    if user.get("is_superuser"):
        return True
    return codename in user.get("_permissions", set())

panel = AdminPanel(
    auth=...,
    permission_checker=my_checker,
)
```

## Configuration

```python
AdminPanel(
    title="Acme Admin",       # shown in sidebar header and browser tab
    prefix="/admin",          # URL prefix for all admin routes
    brand_color="#6366f1",    # hex colour for sidebar and buttons
    logo_url="/static/logo.png",  # optional logo, replaces text title
    per_page=25,              # default pagination size
)
```

## Running the example app

```bash
git clone https://github.com/yourname/nuru
cd nuru
pip install -e .

# Build the Tailwind CSS (requires Node ≥ 18)
npm install
npm run build:css

uvicorn example_app.main:app --reload
# open http://localhost:8000/admin
```

> **Developing?** Run `npm run watch:css` in a second terminal while uvicorn is running to rebuild the stylesheet automatically as you edit templates.

## CSS build

Nuru uses **Tailwind CSS v4** compiled to a single static file (`nuru/static/tailwind.css`) shipped with the package. The pre-built stylesheet is committed to the repo so end-users need no Node toolchain to *use* Nuru — only contributors who edit templates need to rebuild it.

| Command | Effect |
|---|---|
| `npm install` | Install `tailwindcss` + `@tailwindcss/cli` |
| `npm run build:css` | One-off minified build → `nuru/static/tailwind.css` |
| `npm run watch:css` | Rebuild on every template save |

The input CSS lives at `nuru/static/tailwind.input.css` and uses Tailwind 4's CSS-first configuration. All Tailwind theme colors (`--color-indigo-500`, `--color-gray-200`, etc.) are exposed as native CSS custom properties on `:root` by the built stylesheet — no JavaScript probing needed.

## Custom Tailwind classes

Nuru's pre-built `tailwind.css` only scans Nuru's own templates. If your `Resource`, `Page`, or custom Jinja templates use Tailwind utility classes that aren't already present in Nuru's templates, those classes won't be included in the built stylesheet.

### Option 1 — supplemental stylesheet (recommended)

Build a second, project-level stylesheet that covers only your application code, then pass it to `AdminPanel` via `extra_css`:

```css
/* my_app/static/admin-extra.input.css */
@import "tailwindcss";

/* Point at your own code */
@source "../**/*.py";
@source "../templates/**/*.html";

@variant dark (&:where(.dark, .dark *));
```

```bash
# reuse Nuru's node_modules, or install tailwindcss in your project
./node_modules/.bin/tailwindcss \
  -i my_app/static/admin-extra.input.css \
  -o my_app/static/admin-extra.css \
  --minify
```

```python
# app setup
panel = AdminPanel(
    prefix="/admin",
    extra_css="/static/admin-extra.css",          # single URL
    # extra_css=["/static/a.css", "/static/b.css"],  # or a list
)
```

The `extra_css` stylesheets are loaded **after** Nuru's stylesheet, so your utilities can safely complement or override it.

### Option 2 — replace Nuru's stylesheet entirely

If you prefer a single request, build one stylesheet that covers both Nuru's templates and your own code, then serve it at `{prefix}/static/tailwind.css` via a higher-priority `StaticFiles` mount:

```css
/* my_app/static/tailwind.input.css */
@import "tailwindcss";

/* Nuru's own templates */
@source "/path/to/site-packages/nuru/templates/**/*.html";

/* Your application code */
@source "../**/*.py";
@source "../templates/**/*.html";

@variant dark (&:where(.dark, .dark *));
```

Build and mount before Nuru's route:

```python
from starlette.staticfiles import StaticFiles

app.mount("/admin/static", StaticFiles(directory="my_app/static"), name="admin-static")
```

## What's shipped

- ✅ **Core CRUD** — tables, forms, detail views
- ✅ **Typed columns** — `Text`, `Badge`, `Currency`, `DateTime`, `Boolean`
- ✅ **Typed fields** — `Text`, `Email`, `Password`, `Number`, `Textarea`, `Select`, `Checkbox`, `Date`, `Time`, `Hidden`
- ✅ **HTMX interactions** — live search, sort, pagination without page reloads
- ✅ **Actions** — row actions, list actions, form actions, confirm modals, action forms
- ✅ **SQLModel integration** — auto-CRUD and auto-generated columns/fields
- ✅ **Auth** — signed-cookie session, `SimpleAuthBackend`, `DatabaseAuthBackend`, pluggable `AuthBackend`
- ✅ **Roles & Permissions** — `Permission`, `Role`, `RolePermission`, `UserRole` tables; `db_permission_checker`; `panel.sync_permissions()`
- ✅ **Dark mode** — built-in, localStorage-persisted
- ✅ **Responsive** — mobile sidebar, Tailwind CSS

## What's coming

- **Phase 5** — Dashboard widgets: stat cards, line charts, pie charts
- **Phase 6** — Role management UI (permission checkbox grid, user-role assignment from admin panel)
