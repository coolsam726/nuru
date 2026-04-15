"""
WSGI entry point for PythonAnywhere (free tier).

Place this file at:
  /var/www/coolsam_pythonanywhere_com_wsgi.py

Web tab settings:
  Virtualenv:  /home/coolsam/.virtualenvs/nuru
  WSGI file:   /var/www/coolsam_pythonanywhere_com_wsgi.py

How it works
------------
PythonAnywhere free accounts only support WSGI.
FastAPI/nuru is ASGI.  `a2wsgi` bridges the gap.

The FastAPI lifespan (DB schema creation + seeding) is driven in a
background thread that owns a persistent event loop for the process
lifetime.  `future.result(timeout=120)` blocks import until startup
completes, so the first request arrives to a fully-ready app.

Limitations of ASGI-on-WSGI (via a2wsgi)
-----------------------------------------
  - Works for standard HTTP traffic.
  - No WebSocket or SSE support on free PA.
"""

import sys, os, asyncio, threading

# ── sys.path ──────────────────────────────────────────────────────────────────
project_home = "/home/coolsam/nuru_demo"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# ── DB path ───────────────────────────────────────────────────────────────────
os.environ.setdefault("NURU_DB_PATH", f"{project_home}/example_db.sqlite3")

# ── Import app ────────────────────────────────────────────────────────────────
from example_app.main import app as _asgi_app  # noqa: E402

# ── Persistent event loop in a daemon thread ──────────────────────────────────
# a2wsgi will submit coroutines to this loop via run_coroutine_threadsafe.
_loop = asyncio.new_event_loop()
threading.Thread(target=_loop.run_forever, daemon=True).start()

# ── Run lifespan startup now, block until done ────────────────────────────────
# Holding _lifespan_ctx open keeps the async engine alive for the process
# lifetime; shutdown fires when the thread eventually joins on worker exit.
_lifespan_ctx = _asgi_app.router.lifespan_context(_asgi_app)
asyncio.run_coroutine_threadsafe(
    _lifespan_ctx.__aenter__(), _loop
).result(timeout=120)

# ── WSGI application ──────────────────────────────────────────────────────────
from a2wsgi import ASGIMiddleware  # noqa: E402

application = ASGIMiddleware(_asgi_app, lifespan="off")
