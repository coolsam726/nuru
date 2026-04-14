# nuru

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
- ✅ **Auth** — signed-cookie session, `SimpleAuthBackend`, pluggable `AuthBackend`
- ✅ **Dark mode** — built-in, localStorage-persisted
- ✅ **Responsive** — mobile sidebar, Tailwind CSS

## What's coming

- **Phase 5** — Dashboard widgets: stat cards, line charts, pie charts
- **Phase 6** — Multi-user auth and role-based access control
