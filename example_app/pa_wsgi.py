"""
WSGI entry point for PythonAnywhere (free tier).

Place this file at:
  /var/www/coolsam_pythonanywhere_com_wsgi.py

And set these in the PythonAnywhere Web tab:
  Source code:  /home/coolsam/nuru_demo   (where you cloned/copied the repo)
  Virtualenv:   /home/coolsam/.virtualenvs/nuru
  WSGI file:    /var/www/coolsam_pythonanywhere_com_wsgi.py

How it works
------------
PythonAnywhere free accounts only support WSGI.
FastAPI / nuru is ASGI.  The `a2wsgi` library bridges the gap by
wrapping the ASGI app in a synchronous WSGI callable that PA can load.

Limitations of ASGI-on-WSGI (via a2wsgi)
-----------------------------------------
  - Works perfectly for standard HTTP traffic.
  - No WebSocket support (PA free doesn't expose WS anyway).
  - Server-Sent Events (SSE) are not supported.
"""

import sys, os

# ── Add the repo root to sys.path so `example_app` is importable ─────────────
project_home = "/home/coolsam/nuru_demo"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# ── Point the SQLite DB at a writable absolute path ───────────────────────────
# example_app/main.py uses a relative path ("example_db.sqlite3") which would
# resolve to the server's cwd (usually /) on PA.  Override it here.
os.environ.setdefault("NURU_DB_PATH", f"{project_home}/example_db.sqlite3")

# ── Import the FastAPI ASGI app from the existing example_app ─────────────────
from example_app.main import app as _asgi_app  # noqa: E402

# ── Wrap ASGI → WSGI using a2wsgi ────────────────────────────────────────────
from a2wsgi import ASGIMiddleware

application = ASGIMiddleware(_asgi_app)
