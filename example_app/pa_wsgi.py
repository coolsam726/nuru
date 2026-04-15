"""
WSGI entry point for PythonAnywhere (free tier).

Place this file at:
  /var/www/coolsam_pythonanywhere_com_wsgi.py

Web tab settings:
  Virtualenv:  /home/coolsam/.virtualenvs/nuru
  WSGI file:   /var/www/coolsam_pythonanywhere_com_wsgi.py
"""

import sys, os, asyncio

# ── sys.path ──────────────────────────────────────────────────────────────────
project_home = "/home/coolsam/nuru_demo"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# ── DB path (must be absolute and writable on PA) ─────────────────────────────
os.environ.setdefault("NURU_DB_PATH", f"{project_home}/example_db.sqlite3")

# ── Import app ────────────────────────────────────────────────────────────────
from example_app.main import app as _asgi_app  # noqa: E402

# ── Run lifespan startup eagerly (schema sync + seed) ────────────────────────
# asyncio.run() creates a temporary loop, runs startup, then closes it.
# Because SQLite is file-based, the tables and seeded data persist on disk.
# Subsequent requests open fresh connections to the same file — this is fine.
async def _run_startup():
    ctx = _asgi_app.router.lifespan_context(_asgi_app)
    await ctx.__aenter__()          # runs everything up to `yield` in _lifespan
    # No __aexit__ — we intentionally leave the context open so any module-level
    # state set during startup (e.g. sync_permissions cache) stays alive.

asyncio.run(_run_startup())

# Prevent a2wsgi from running lifespan again on the first request.
# `lifespan` (not `lifespan_handler`) is the actual FastAPI Router attribute
# that a2wsgi reads via `lifespan_context`. Setting it to None disables re-run.
_asgi_app.router.lifespan = None

# ── WSGI application ──────────────────────────────────────────────────────────
from a2wsgi import ASGIMiddleware  # noqa: E402

application = ASGIMiddleware(_asgi_app)
