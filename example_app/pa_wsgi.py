"""
WSGI entry point for PythonAnywhere (free tier).

Place this file at:
  /var/www/coolsam_pythonanywhere_com_wsgi.py

And set these in the PythonAnywhere Web tab:
  Source code:  /home/coolsam/nuru_demo
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

# ── Add the project directory to sys.path ─────────────────────────────────────
project_home = "/home/coolsam/nuru_demo"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# ── Import the FastAPI ASGI app ───────────────────────────────────────────────
from pa_app import app as _asgi_app  # noqa: E402

# ── Wrap ASGI → WSGI using a2wsgi ────────────────────────────────────────────
from a2wsgi import ASGIMiddleware

application = ASGIMiddleware(_asgi_app)
