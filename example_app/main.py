"""
Kibrary — Nuru Library Demo  (v0.4 API)
=======================================

Run with:  uvicorn example_app.main:app --reload

  /admin  — auth-protected  (user: admin@kibrary.org / pass: secret)
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlmodel import SQLModel

from nuru.panels.base import Panel
from nuru.integrations.flowbite import register_flowbite
import nuru.roles  # noqa: F401 — ensures role tables are registered

# Import models so SQLModel metadata is populated before schema sync
import example_app.models  # noqa: F401

from example_app.db import engine, get_session
from example_app.auth import auth_backend, permission_checker
from example_app.seed import seed_all

_TEMPLATES_DIR = Path(__file__).parent / "templates"


# ---------------------------------------------------------------------------
# Panel definition
# ---------------------------------------------------------------------------

class KibraryPanel(Panel):
    title              = "Kibrary Admin"
    prefix             = "/admin"
    primary_color      = "var(--color-amber-500)"
    auth_backend       = auth_backend
    permission_checker = permission_checker
    per_page           = 10


panel = KibraryPanel()
panel.add_template_dir(_TEMPLATES_DIR)
register_flowbite(panel)


# ---------------------------------------------------------------------------
# App + lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _lifespan(app: FastAPI):
    from nuru.migrations import sync_schema
    await sync_schema(engine, SQLModel.metadata)
    await panel._legacy.sync_permissions(get_session)
    await seed_all()
    yield


app = FastAPI(title="Kibrary — Nuru Library Demo", lifespan=_lifespan)
panel.mount(app)
