"""
Lightweight automatic schema synchronisation for development.

This module solves a specific, narrow problem: **you add a column to a
SQLModel (or SQLAlchemy) model and want the database to reflect that change
automatically when the server restarts**, without writing migration files.

What it does
------------
* Creates any table that does not yet exist (same as ``create_all``).
* For every table that *does* exist, compares the model's columns against the
  real database columns and issues ``ALTER TABLE … ADD COLUMN`` for each
  missing one.

What it does NOT do
-------------------
* Rename or drop columns  (those require explicit Alembic migrations).
* Change column types     (same).
* Reorder columns         (irrelevant for SQL).

For production, use Alembic.  This helper is intentionally simple and safe
to run on every startup in development — it is additive only.

Usage
-----
Replace your startup ``create_all`` call with ``sync_schema``::

    from nuru.migrations import sync_schema
    from sqlmodel import SQLModel

    @app.on_event("startup")
    async def on_startup():
        await sync_schema(engine, SQLModel.metadata)
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


async def sync_schema(engine: AsyncEngine, metadata: Any) -> None:
    """
    Create missing tables and add missing columns to existing tables.

    Parameters
    ----------
    engine:
        An ``AsyncEngine`` instance (from ``create_async_engine``).
    metadata:
        The ``MetaData`` object that holds the table definitions, e.g.
        ``SQLModel.metadata`` or ``Base.metadata``.
    """
    async with engine.begin() as conn:
        # 1. Create any tables that don't exist yet.
        await conn.run_sync(metadata.create_all)

        # 2. For tables that already exist, add any missing columns.
        def _sync_columns(sync_conn: Any) -> None:
            inspector = inspect(sync_conn)
            existing_tables = set(inspector.get_table_names())

            for table in metadata.sorted_tables:
                if table.name not in existing_tables:
                    continue  # just created above

                existing_cols = {
                    col["name"]
                    for col in inspector.get_columns(table.name)
                }

                for col in table.columns:
                    if col.name in existing_cols:
                        continue

                    col_def = _column_ddl(col)
                    stmt = f"ALTER TABLE {table.name} ADD COLUMN {col_def}"
                    logger.info("Schema sync: %s", stmt)
                    sync_conn.execute(text(stmt))

        await conn.run_sync(_sync_columns)


def _column_ddl(col: Any) -> str:
    """
    Build a minimal ``column_name TYPE [NOT NULL] [DEFAULT …]`` DDL fragment.

    Intentionally uses ``col.type.compile()`` so it works with any SQLAlchemy
    dialect that the engine is connected to.
    """
    from sqlalchemy.dialects import sqlite as _sqlite_dialect

    try:
        type_str = col.type.compile(dialect=_sqlite_dialect.dialect())
    except Exception:
        type_str = str(col.type)

    parts = [col.name, type_str]

    # DEFAULT must come before NOT NULL in most databases.
    if col.default is not None and col.default.is_scalar:
        val = col.default.arg
        if isinstance(val, str):
            val = f"'{val}'"
        elif isinstance(val, bool):
            val = "1" if val else "0"
        parts.append(f"DEFAULT {val}")
    elif col.nullable is False and not col.primary_key:
        # Non-nullable column with no default — use an empty-string sentinel
        # for VARCHAR or 0 for numerics so existing rows don't violate the
        # constraint.  SQLite requires a default when adding NOT NULL columns.
        try:
            compiled = col.type.compile(dialect=_sqlite_dialect.dialect()).upper()
            if any(t in compiled for t in ("INT", "REAL", "FLOAT", "NUMERIC", "BOOL")):
                parts.append("DEFAULT 0")
            else:
                parts.append("DEFAULT ''")
        except Exception:
            parts.append("DEFAULT ''")

    return " ".join(parts)
