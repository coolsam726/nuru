from __future__ import annotations
"""
Backward-compatibility shim.

``SQLModelResource`` has been merged into :class:`nuru.Resource`.
Just use ``Resource`` directly — setting ``model`` and ``session_factory``
class attributes activates the SQLModel CRUD automatically.

This module is kept so existing imports don't break::

    from nuru.integrations.sqlmodel import SQLModelResource  # still works
"""
from nuru.resource import Resource


__all__ = ["Resource"]
""""
Usage::

    from sqlmodel import SQLModel, Field
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from contextlib import asynccontextmanager

    from nuru.integrations.sqlmodel import Resource

    engine = create_async_engine("sqlite+aiosqlite:///app.db")
    _SessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def get_session():
        async with _SessionFactory() as session:
            yield session

    class User(SQLModel, table=True):
        id: int | None = Field(default=None, primary_key=True)
        name: str
        email: str
        active: bool = True

    class UserResource(Resource):
        label = "User"
        label_plural = "Users"
        model = User
        session_factory = get_session
        search_fields = ["name", "email"]   # optional
"""

from typing import Any, ClassVar, Union, get_args, get_origin

from sqlalchemy import func, or_
from sqlmodel import select

from nuru import Resource, columns, fields


# ---------------------------------------------------------------------------
# Type-inspection helpers
# ---------------------------------------------------------------------------

def _unwrap_optional(annotation: Any) -> Any:
    """Strip ``Optional[X]`` / ``Union[X, None]`` down to ``X``."""
    if get_origin(annotation) is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        return args[0] if args else annotation
    return annotation


def _annotation_to_column(key: str, annotation: Any) -> columns.Column:
    inner = _unwrap_optional(annotation)
    name  = getattr(inner, "__name__", "")
    if inner is bool:
        return columns.Boolean(key=key)
    if name in ("date",):
        return columns.DateTime(key=key, date_only=True)
    if name in ("datetime",):
        return columns.DateTime(key=key)
    return columns.Text(key=key, sortable=True)


def _annotation_to_field(key: str, annotation: Any) -> fields.Field:
    inner = _unwrap_optional(annotation)
    name  = getattr(inner, "__name__", "")
    if inner is bool:
        return fields.Checkbox(key=key)
    if inner is int or name in ("int",):
        return fields.Number(key=key)
    if inner is float or name in ("float", "Decimal"):
        return fields.Number(key=key)
    if name == "date":
        return fields.Date(key=key)
    if name == "datetime":
        return fields.Text(key=key, input_type="datetime-local")
    # Enum → Select
    try:
        if issubclass(inner, __builtins__["__import__"]("enum").Enum):  # type: ignore[index]
            return fields.Select(key=key, options=[e.value for e in inner])
    except (TypeError, KeyError):
        pass
    return fields.Text(key=key)


# ---------------------------------------------------------------------------
# SQLModelResource
# ---------------------------------------------------------------------------

class SQLModelResource(Resource):
    """
    Resource subclass that auto-wires CRUD to a SQLModel table.

    Class-level declarations
    ------------------------
    model           : the SQLModel class (must have ``table=True``).
    session_factory : zero-argument async context-manager factory that yields
                      an ``AsyncSession``.  See module docstring for an example.
    search_fields   : list of string-column names to enable search against.

    ``table_columns`` and ``form_fields`` are auto-generated from the model's
    field annotations.  Override them as normal class attributes to customise.
    """

    model:           ClassVar[Any]
    session_factory: ClassVar[Any]   # Callable[[], AsyncContextManager[AsyncSession]]
    search_fields:   ClassVar[list[str]] = []

    # ------------------------------------------------------------------
    # Auto-build on subclass definition
    # ------------------------------------------------------------------

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "model"):
            cls._auto_build()

    @classmethod
    def _pk_name(cls) -> str:
        try:
            pk_cols = list(cls.model.__table__.primary_key.columns)
            return pk_cols[0].key if pk_cols else "id"
        except AttributeError:
            return "id"

    @classmethod
    def _auto_build(cls) -> None:
        """Populate table_columns and form_fields from the model if not set."""
        if cls.table_columns and cls.form_fields:
            return  # fully user-supplied — leave as-is
        try:
            model_fields = cls.model.model_fields
        except AttributeError:
            return

        pk = cls._pk_name()
        auto_cols: list[columns.Column] = []
        auto_flds: list[fields.Field]   = []

        for fname, finfo in model_fields.items():
            if fname == pk:
                continue
            ann = finfo.annotation or str
            auto_cols.append(_annotation_to_column(fname, ann))
            auto_flds.append(_annotation_to_field(fname, ann))

        if not cls.table_columns:
            cls.table_columns = auto_cols
        if not cls.form_fields:
            cls.form_fields = auto_flds

    # ------------------------------------------------------------------
    # CRUD hooks
    # ------------------------------------------------------------------

    def _coerce_pk(self, id: Any) -> Any:
        pk = self._pk_name()
        try:
            pk_ann = _unwrap_optional(self.model.model_fields[pk].annotation)
            return pk_ann(id)
        except (KeyError, TypeError, ValueError):
            return id

    async def get_list(
        self,
        *,
        page: int = 1,
        per_page: int = 25,
        search: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        filters: dict | None = None,
    ) -> dict:
        async with type(self).session_factory() as session:
            query   = select(self.model)
            count_q = select(func.count()).select_from(self.model)

            if search and self.search_fields:
                conditions = [
                    getattr(self.model, f).ilike(f"%{search}%")
                    for f in self.search_fields
                    if hasattr(self.model, f)
                ]
                if conditions:
                    query   = query.where(or_(*conditions))
                    count_q = count_q.where(or_(*conditions))

            total = (await session.exec(count_q)).one()

            if sort_by and hasattr(self.model, sort_by):
                col_attr = getattr(self.model, sort_by)
                query = query.order_by(
                    col_attr.desc() if sort_dir == "desc" else col_attr.asc()
                )

            query   = query.offset((page - 1) * per_page).limit(per_page)
            records = (await session.exec(query)).all()
            return {"records": records, "total": total}

    async def get_record(self, id: Any) -> Any:
        async with type(self).session_factory() as session:
            return await session.get(self.model, self._coerce_pk(id))

    async def save_record(self, id: Any | None, data: dict) -> Any:
        async with type(self).session_factory() as session:
            if id is None:
                record = self.model(**data)
            else:
                record = await session.get(self.model, self._coerce_pk(id))
                if record is None:
                    raise ValueError(f"{self.model.__name__} #{id} not found")
                for k, v in data.items():
                    setattr(record, k, v)
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record

    async def delete_record(self, id: Any) -> None:
        async with type(self).session_factory() as session:
            record = await session.get(self.model, self._coerce_pk(id))
            if record:
                await session.delete(record)
                await session.commit()
