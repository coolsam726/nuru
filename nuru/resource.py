from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Union, get_args, get_origin, TYPE_CHECKING
from datetime import date, datetime
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from .icons import resolve_icon
import inspect

if TYPE_CHECKING:
    from .panel import AdminPanel


# ---------------------------------------------------------------------------
# Builtin row-action sentinel (view / edit / delete)
# ---------------------------------------------------------------------------

@dataclass
class _BuiltinAction:
    """Sentinel for the three built-in per-row operations.

    Unlike ``Action``, these are rendered as links or hx-delete buttons by
    the template, not as ``data-action-trigger`` modals.
    """
    key: str        # '__view__' | '__edit__' | '__delete__'
    label: str
    icon: str
    style: str = "default"
    is_builtin: bool = True


# ---------------------------------------------------------------------------
# Internal helpers for auto-building columns/fields from SQLModel annotations
# ---------------------------------------------------------------------------

def _unwrap_optional(annotation: Any) -> Any:
    if get_origin(annotation) is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        return args[0] if args else annotation
    return annotation


def _annotation_to_column(key: str, annotation: Any) -> Any:
    from . import columns
    inner = _unwrap_optional(annotation)
    name  = getattr(inner, "__name__", "")
    if inner is bool:
        return columns.Boolean(key=key)
    if name == "date":
        return columns.DateTime(key=key, date_only=True)
    if name == "datetime":
        return columns.DateTime(key=key)
    return columns.Text(key=key, sortable=True)


def _annotation_to_field(key: str, annotation: Any) -> Any:
    from . import fields
    import enum as _enum
    inner = _unwrap_optional(annotation)
    name  = getattr(inner, "__name__", "")
    if inner is bool:
        return fields.Checkbox(key=key)
    if inner is int or name == "int":
        return fields.Number(key=key)
    if inner is float or name in ("float", "Decimal"):
        return fields.Number(key=key)
    if name == "date":
        return fields.Date(key=key)
    if name == "datetime":
        return fields.Text(key=key, input_type="datetime-local")
    try:
        if issubclass(inner, _enum.Enum):
            return fields.Select(key=key, options=[e.value for e in inner])
    except TypeError:
        pass
    return fields.Text(key=key)


class Resource:
    """
    Base class for all admin resources.

    Subclass this and define `label`, `table_columns`, `form_fields`,
    and override the four data hooks to connect your service or ORM layer.

    Example::

        class UserResource(Resource):
            label = "User"
            label_plural = "Users"

            table_columns = [...]
            form_fields = [...]

            async def get_list(self, *, page, per_page, search, **kwargs):
                return await user_service.list(page=page, search=search)

            async def get_record(self, id):
                return await user_service.get(id)

            async def save_record(self, id, data):
                if id is None:
                    return await user_service.create(data)
                return await user_service.update(id, data)

            async def delete_record(self, id):
                await user_service.delete(id)
    """

    # ------------------------------------------------------------------
    # Class-level declarations — override in subclasses
    # ------------------------------------------------------------------

    label: str = ""
    label_plural: str = ""
    slug: str = ""
    icon: str = "table"
    show_in_nav: bool = True
    nav_label: str = ""
    nav_icon: str = ""
    nav_sort: int = 100

    table_columns: list = []
    form_fields: list = []
    detail_fields: list = []  # if empty, falls back to form_fields
    form_cols: int = 1        # top-level column count for bare fields (1–4)
    row_actions: list = []
    bulk_actions: list = []
    list_actions: list = []   # Action instances shown in the list-page header
    form_actions: list = []   # Action instances shown in the form-page header / inline

    # Permissions — set to False on a subclass to disable those operations.
    can_create: bool = True
    can_edit:   bool = True
    can_delete: bool = True
    can_view:   bool = True

    # ------------------------------------------------------------------
    # Optional SQLModel / SQLAlchemy wiring
    # Set these on a subclass to get automatic CRUD without overriding
    # get_list / get_record / save_record / delete_record.
    #
    #   model           — SQLModel class with table=True
    #   session_factory — zero-arg async context-manager that yields AsyncSession
    #   search_fields   — column names to enable ilike search on
    # ------------------------------------------------------------------
    model:           ClassVar[Any] = None
    session_factory: ClassVar[Any] = None   # Callable[[], AsyncContextManager[AsyncSession]]
    search_fields:   ClassVar[list[str]] = []
    # SQLAlchemy loader options applied to the automatic get_list query, e.g.:
    #   from sqlalchemy.orm import selectinload
    #   load_options = [selectinload(Book.author), selectinload(Book.subject)]
    load_options:    ClassVar[list] = []

    # ------------------------------------------------------------------
    # Options endpoint — used by BelongsTo fields to populate their selectors.
    #
    #   options_value_field — attr on each record to use as the option value;
    #                         defaults to the model's primary key.
    #   options_label_field — attr on each record to use as the option label;
    #                         defaults to str(record).
    #   options_per_page    — max records returned by GET /options (default 200).
    # ------------------------------------------------------------------
    options_value_field: ClassVar[str] = ""
    options_label_field: ClassVar[str] = ""
    options_per_page:    ClassVar[int] = 200

    # ------------------------------------------------------------------
    # Auto-build columns/fields from SQLModel annotations when model is set
    # ------------------------------------------------------------------

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.__dict__.get("model") is not None:
            cls._auto_build_from_model()

    @classmethod
    def _pk_name(cls) -> str:
        try:
            pk_cols = list(cls.model.__table__.primary_key.columns)
            return pk_cols[0].key if pk_cols else "id"
        except AttributeError:
            return "id"

    @classmethod
    def _auto_build_from_model(cls) -> None:
        """Populate table_columns / form_fields from the model's annotations
        if the subclass hasn't defined them explicitly."""
        # Only fill in what the subclass left blank.
        if cls.__dict__.get("table_columns") and cls.__dict__.get("form_fields"):
            return
        try:
            model_fields = cls.model.model_fields
        except AttributeError:
            return

        pk = cls._pk_name()
        auto_cols: list = []
        auto_flds: list = []

        for fname, finfo in model_fields.items():
            if fname == pk:
                continue
            ann = finfo.annotation or str
            auto_cols.append(_annotation_to_column(fname, ann))
            auto_flds.append(_annotation_to_field(fname, ann))

        if not cls.__dict__.get("table_columns"):
            cls.table_columns = auto_cols
        if not cls.__dict__.get("form_fields"):
            cls.form_fields = auto_flds

    def _coerce_pk(self, id: Any) -> Any:
        pk = self._pk_name()
        try:
            pk_ann = _unwrap_optional(self.model.model_fields[pk].annotation)
            return pk_ann(id)
        except (KeyError, TypeError, ValueError):
            return id

    def _validate_fields(self, fields: list, data: dict) -> dict:
        """Validate a mapping of submitted form data against a list of Field
        instances. Returns a dict mapping field keys to error messages. Empty
        dict means no errors.
        """
        import re
        from urllib.parse import urlparse

        errors: dict = {}

        for field in fields:
            key = field.get_key()
            val = data.get(key)

            # Required check
            if field.is_required():
                if val is None or (isinstance(val, str) and val.strip() == ""):
                    errors[key] = "This field is required."
                    continue

            # Skip further checks on empty/None values
            if val is None or (isinstance(val, str) and val == ""):
                continue

            # max_length
            max_len = getattr(field, "get_max_length", lambda: None)()
            if max_len is not None and isinstance(val, str) and len(val) > max_len:
                errors[key] = f"Must be at most {max_len} characters."
                continue

            # Validator keywords
            validators = list(getattr(field, "get_validators", lambda: [])() or [])

            # Email
            if "email" in validators:
                # Basic email pattern — server-side check (not exhaustive)
                if not isinstance(val, str) or re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", val) is None:
                    errors[key] = "Enter a valid email address."
                    continue

            # URL
            if "url" in validators:
                try:
                    p = urlparse(val)
                    if not p.scheme or not p.netloc:
                        errors[key] = "Enter a valid URL."
                        continue
                except Exception:
                    errors[key] = "Enter a valid URL."
                    continue

            # Numeric / integer
            if "numeric" in validators or field.get_field_type() == "number":
                try:
                    float(val)
                except Exception:
                    errors[key] = "Enter a numeric value."
                    continue

            if "integer" in validators:
                try:
                    if isinstance(val, str) and val.strip() == "":
                        raise ValueError()
                    intval = int(float(val))
                    if float(intval) != float(val):
                        # e.g. '3.5' -> not integer
                        errors[key] = "Enter an integer value."
                        continue
                except Exception:
                    errors[key] = "Enter an integer value."
                    continue

        return errors

    # ------------------------------------------------------------------
    # Internal setup
    # ------------------------------------------------------------------

    def __init__(self, *, panel: AdminPanel) -> None:
        self.panel = panel
        if not self.slug:
            self.slug = self.label.lower().replace(" ", "-")
        if not self.label_plural:
            self.label_plural = self.label + "s"
        # v0.4 bridge: if subclass defines form()/table()/infolist(),
        # populate legacy form_fields / table_columns / detail_fields from them.
        if callable(getattr(self, "_bridge_from_new_api", None)):
            self._bridge_from_new_api()

    async def _user_allowed(self, request: Request, action: str, action_key: str | None = None) -> bool:
        """Check whether the current user may perform *action* on this resource.

        Codename format: ``{resource_slug}:{action}`` (e.g. ``users:list``).

        For named actions, two codenames are tried in order so that operators
        can grant blanket action access (``orders:action``) or lock it to
        specific keys (``orders:action:export_csv``):

        1. ``{slug}:action:{action_key}`` — specific named action
        2. ``{slug}:action``              — generic action bucket

        The checker may be synchronous or async; both are supported.
        Auth disabled → always allowed.
        """
        if self.panel.auth is None:
            return True

        user = await self.panel._current_user(request)
        checker = getattr(self.panel, "permission_checker", None)
        if checker is None:
            return True

        async def _check(codename: str) -> bool:
            res = checker(user, codename, self)
            if inspect.isawaitable(res):
                res = await res
            return bool(res)

        if action_key is not None:
            # Try specific key first, then generic action bucket.
            return await _check(f"{self.slug}:action:{action_key}") or await _check(f"{self.slug}:action")

        return await _check(f"{self.slug}:{action}")

    @property
    def all_row_actions(self) -> list:
        """Unified list: user-defined row_actions + built-in view/edit/delete.

        Built-ins are appended at the end so user actions appear first.
        The template renders them all through the same inline/overflow logic.
        """
        builtins = []
        if self.can_view:
            builtins.append(_BuiltinAction(
                key="__view__", label="View", style="default",
                icon="M15 12a3 3 0 11-6 0 3 3 0 016 0zM2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z",
            ))
        if self.can_edit:
            builtins.append(_BuiltinAction(
                key="__edit__", label="Edit", style="default",
                icon="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z",
            ))
        if self.can_delete:
            builtins.append(_BuiltinAction(
                key="__delete__", label="Delete", style="danger",
                icon="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16",
            ))
        return list(self.row_actions) + builtins

    # ------------------------------------------------------------------
    # Data hooks — override these in your subclass
    # ------------------------------------------------------------------

    async def get_list(
        self,
        *,
        page: int = 1,
        per_page: int = 10,
        search: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        filters: dict | None = None,
    ) -> dict:
        """
        Return a page of records.
        Must return: {"records": [...], "total": int}

        If ``model`` and ``session_factory`` are set, this is handled
        automatically. Otherwise override it in your subclass.
        """
        if type(self).model is not None and type(self).session_factory is not None:
            from sqlalchemy import func, or_
            from sqlmodel import select
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
                for opt in type(self).load_options:
                    query = query.options(opt)
                query   = query.offset((page - 1) * per_page).limit(per_page)
                records = (await session.exec(query)).all()
                return {"records": records, "total": total}
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement get_list()"
        )

    async def get_record(self, id: Any) -> Any:
        """Return a single record by primary key.

        If ``model`` and ``session_factory`` are set, this is handled
        automatically. Otherwise override it in your subclass.
        """
        if type(self).model is not None and type(self).session_factory is not None:
            async with type(self).session_factory() as session:
                return await session.get(self.model, self._coerce_pk(id))
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement get_record()"
        )

    async def save_record(self, id: Any | None, data: dict) -> Any:
        """
        Create (id is None) or update (id is set) a record.
        Return the saved record.

        If ``model`` and ``session_factory`` are set, this is handled
        automatically. Otherwise override it in your subclass.
        """
        if type(self).model is not None and type(self).session_factory is not None:
            async with type(self).session_factory() as session:
                # Exclude list values (M2M / checkbox_group fields) — they are
                # handled by after_save() and have no scalar column to write to.
                scalar_data = {k: v for k, v in data.items() if not isinstance(v, list)}
                # Coerce date/datetime string values into Python objects so
                # SQLModel / SQLAlchemy inserts the correct types. Form inputs
                # submit ISO date strings (YYYY-MM-DD) and datetimes in
                # ISO format; convert them here before constructing the model.
                for k, v in list(scalar_data.items()):
                    if v is None:
                        continue
                    # Empty strings should be treated as NULL
                    if v == "":
                        scalar_data[k] = None
                        continue
                    try:
                        ann = type(self).model.model_fields[k].annotation
                    except Exception:
                        ann = None
                    if ann is None:
                        continue
                    inner = _unwrap_optional(ann)
                    name = getattr(inner, "__name__", "")
                    if name == "date" and isinstance(v, str):
                        try:
                            scalar_data[k] = date.fromisoformat(v)
                        except Exception:
                            # Leave as-is; DB will raise a helpful error later
                            pass
                    elif name == "datetime" and isinstance(v, str):
                        try:
                            scalar_data[k] = datetime.fromisoformat(v)
                        except Exception:
                            pass
                if id is None:
                    record = self.model(**scalar_data)
                else:
                    record = await session.get(self.model, self._coerce_pk(id))
                    if record is None:
                        raise ValueError(f"{self.model.__name__} #{id} not found")
                    for k, v in scalar_data.items():
                        setattr(record, k, v)
                session.add(record)
                await session.commit()
                await session.refresh(record)
                return record
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement save_record()"
        )

    async def after_save(self, record_id: Any, data: dict) -> None:
        """Hook called after save_record succeeds.

        Override in your subclass to handle M2M relationships or any
        post-save side effects.  ``data`` is the full parsed form dict,
        including any list-valued ``CheckboxGroup`` fields that were
        deliberately excluded from the main ``save_record`` call.
        """

    async def get_options(self, *, q: str | None = None) -> list[dict]:
        """Return ``[{"value": ..., "label": ...}]`` for BelongsTo field selectors.

        Called by the ``GET /{slug}/options`` JSON endpoint.  Override this
        method in your subclass for full control: apply extra filters, order
        differently, or source records from anywhere.

        The default implementation calls :meth:`get_list` using the supplied
        search query and maps each record through ``options_value_field`` and
        ``options_label_field``.  Adjust those class-level variables instead
        of overriding when only the attribute names need changing.
        """
        try:
            result = await self.get_list(
                page=1,
                per_page=type(self).options_per_page,
                search=q or None,
            )
        except NotImplementedError:
            return []

        pk = self._pk_name()
        value_attr = type(self).options_value_field or pk
        label_attr = type(self).options_label_field

        out: list[dict] = []
        for rec in result.get("records", []):
            v = getattr(rec, value_attr, None)
            lbl = getattr(rec, label_attr, None) if label_attr else str(rec)
            out.append({
                "value": str(v)   if v   is not None else "",
                "label": str(lbl) if lbl is not None else "",
            })
        return out

    async def delete_record(self, id: Any) -> None:
        """Delete a record by primary key.

        If ``model`` and ``session_factory`` are set, this is handled
        automatically. Otherwise override it in your subclass.
        """
        if type(self).model is not None and type(self).session_factory is not None:
            async with type(self).session_factory() as session:
                record = await session.get(self.model, self._coerce_pk(id))
                if record:
                    await session.delete(record)
                    await session.commit()
            return
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement delete_record()"
        )

    async def _dispatch_action(
        self,
        action_key: str,
        record_id: Any | None,
        data: dict,
        request: Request,
    ) -> Any:
        """
        Locate the :class:`~nuru.actions.Action` whose ``key`` matches
        ``action_key`` across all action lists, then call the method named by
        ``action.handler`` on this resource instance.

        Handler signature::

            async def my_handler(self, record_id, data, request)

        ``record_id`` is ``None`` for list-level actions.
        ``data`` is the dict collected by the modal (empty dict if no form).
        Return ``None`` for the default redirect, or a URL string to
        redirect elsewhere.
        """
        action = None
        for lst in (self.row_actions, self.list_actions, self.form_actions):
            for a in lst:
                if a.key == action_key:
                    action = a
                    break
            if action:
                break

        if action is None:
            raise LookupError(
                f"No action with key '{action_key}' registered on "
                f"{self.__class__.__name__}"
            )

        method = getattr(self, action.handler, None)
        if method is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} has no method '{action.handler}' "
                f"(required by action '{action_key}')"
            )

        import inspect
        if inspect.iscoroutinefunction(method):
            return await method(record_id, data, request)
        return method(record_id, data, request)

    # ------------------------------------------------------------------
    # Form data parsing — override to add type coercion if needed
    # ------------------------------------------------------------------

    async def parse_action_form(self, request: Request) -> dict:
        """
        Parse the data submitted by an action modal.

        Returns all non-underscore-prefixed form fields as a plain dict.
        Override to add type coercion if needed.
        """
        form_data = await request.form()
        return {k: v for k, v in form_data.items() if not k.startswith("_")}

    async def parse_form(self, request: Request) -> dict:
        """
        Parse incoming form data into a plain dict.

        Handles checkbox fields correctly (absent checkbox = False).
        Override this to add type coercion (e.g. int/date fields).
        """
        form_data = await request.form()
        data: dict[str, Any] = {}
        submitted = dict(form_data)

        for field in self._flat_form_fields:
            key = field.get_key()
            if field.get_field_type() == "checkbox":
                data[key] = submitted.get(key) == "true"
            elif field.get_field_type() == "checkbox_group":
                # Multi-value: collect all submitted values for this key.
                data[key] = form_data.getlist(key)
            elif field.get_field_type() == "file_upload":
                # FilePond posts the server IDs as one or more values under the field name.
                # Multiple values come in as repeated fields; single value is a plain string.
                vals = form_data.getlist(key)
                # Flatten — FilePond may also send a JSON-encoded list
                server_ids: list[str] = []
                import json as _json
                for v in vals:
                    if not v:
                        continue
                    try:
                        parsed = _json.loads(v)
                        if isinstance(parsed, list):
                            server_ids.extend([str(x) for x in parsed if x])
                            continue
                    except (ValueError, TypeError):
                        pass
                    server_ids.append(v)
                if not server_ids:
                    data[key] = None
                elif getattr(field, "is_multiple", lambda: False)():
                    import json as _j2
                    data[key] = _j2.dumps(server_ids)
                else:
                    data[key] = server_ids[0]
            elif field.get_field_type() == "datetimepicker":
                # Submits as two keys: {key}_date and {key}_time.
                date_val = submitted.get(f"{key}_date", "") or ""
                time_val = submitted.get(f"{key}_time", "") or ""
                if date_val and time_val:
                    data[key] = f"{date_val} {time_val}"
                elif date_val:
                    data[key] = date_val
                else:
                    data[key] = None
            elif key in submitted:
                if key.startswith("_"):
                    continue
                value = submitted[key]
                data[key] = value if value != "" else None
            else:
                data[key] = None

        return data

    @property
    def _flat_form_fields(self) -> list:
        """Flatten form_fields, expanding any Section containers into their fields."""
        flat = []
        for item in self.form_fields:
            if item.is_section_field():
                flat.extend(item.get_fields())
            else:
                flat.append(item)
        return flat

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_list(
        self,
        *,
        page: int,
        search: str | None,
        sort_by: str | None,
        sort_dir: str,
    ) -> dict:
        """Shared data-fetching logic used by both full-page and HTMX routes."""
        per_page = self.panel.per_page
        try:
            result = await self.get_list(
                page=page,
                per_page=per_page,
                search=search,
                sort_by=sort_by,
                sort_dir=sort_dir,
            )
        except NotImplementedError:
            result = {"records": [], "total": 0}

        total = result.get("total", 0)
        return {
            "resource": self,
            "records": result.get("records", []),
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, -(-total // per_page)),  # ceiling division
            "search": search or "",
            "sort_by": sort_by or "",
            "sort_dir": sort_dir,
        }

    # ------------------------------------------------------------------
    # Route registration — called by AdminPanel._build_routes()
    # ------------------------------------------------------------------

    def _register_routes(self, router: APIRouter) -> None:
        resource = self
        prefix = f"/{self.slug}"

        # ---- GET /resource ---- full list page -----------------------
        @router.get(prefix, response_class=HTMLResponse, response_model=None, include_in_schema=False)
        async def list_view(
            request: Request,
            page: int = 1,
            search: str | None = None,
            sort_by: str | None = None,
            sort_dir: str = "asc",
            flash: str | None = None,
        ) -> HTMLResponse | RedirectResponse:
            if (redir := await resource.panel._require_login(request)):
                return redir
            user = await resource.panel._current_user(request)
            if not await resource._user_allowed(request, "list"):
                return await resource.panel._render_error(403, "Access Denied", "You don't have permission to view this resource.", request=request)
            ctx = await resource._fetch_list(
                page=page, search=search,
                sort_by=sort_by, sort_dir=sort_dir,
            )
            ctx["flash"] = flash
            html = resource.panel._render("list.html", ctx, user=user)
            return HTMLResponse(html)

        # ---- GET /resource/table ---- HTMX partial (table only) -----
        #
        # This is the endpoint that search, sort, and pagination all
        # target with hx-get. It returns only the table fragment so
        # HTMX can swap just the #list-container div without touching
        # the rest of the page.
        @router.get(f"{prefix}/table", response_class=HTMLResponse, response_model=None, include_in_schema=False)
        async def table_partial(
            request: Request,
            page: int = 1,
            search: str | None = None,
            sort_by: str | None = None,
            sort_dir: str = "asc",
        ) -> HTMLResponse | RedirectResponse:
            if (redir := await resource.panel._require_login(request)):
                return redir
            ctx = await resource._fetch_list(
                page=page, search=search,
                sort_by=sort_by, sort_dir=sort_dir,
            )
            user = await resource.panel._current_user(request)
            html = resource.panel._render("partials/table.html", ctx, user=user)
            return HTMLResponse(html)

        # ---- GET /resource/new ---- blank create form ----------------
        @router.get(f"{prefix}/new", response_class=HTMLResponse, response_model=None, include_in_schema=False)
        async def create_form_view(request: Request) -> HTMLResponse | RedirectResponse:
            if (redir := await resource.panel._require_login(request)):
                return redir
            if not resource.can_create:
                return await resource.panel._render_error(403, "Access Denied", "Creating records is not allowed for this resource.", request=request)
            if not await resource._user_allowed(request, "create"):
                return await resource.panel._render_error(403, "Access Denied", "You don't have permission to create records here.", request=request)
            user = await resource.panel._current_user(request)
            html = resource.panel._render("form.html", {
                "resource": resource,
                "record": None,
                "record_id": None,
                "errors": {},
            }, user=user)
            return HTMLResponse(html)

        # ---- POST /resource ---- handle create -----------------------
        @router.post(prefix, response_class=HTMLResponse, response_model=None, include_in_schema=False)
        async def create_submit(request: Request) -> HTMLResponse | RedirectResponse:
            if (redir := await resource.panel._require_login(request)):
                return redir
            if not resource.can_create:
                return await resource.panel._render_error(403, "Access Denied", "Creating records is not allowed for this resource.", request=request)
            if not await resource._user_allowed(request, "create"):
                return await resource.panel._render_error(403, "Access Denied", "You don't have permission to create records here.", request=request)
            user = await resource.panel._current_user(request)
            data = await resource.parse_form(request)
            # Server-side validation
            errors = resource._validate_fields(resource._flat_form_fields, data)
            if errors:
                html = resource.panel._render("form.html", {
                    "resource": resource,
                    "record": data,
                    "record_id": None,
                    "errors": errors,
                }, user=user)
                return HTMLResponse(html, status_code=422)
            action = (await request.form()).get("_action", "save")
            try:
                record = await resource.save_record(None, data)
                saved_id = record["id"] if isinstance(record, dict) else getattr(record, "id", None)
                await resource.after_save(saved_id, data)
                if action == "save_and_continue" and saved_id:
                    return RedirectResponse(
                        url=f"{resource.panel.prefix}/{resource.slug}/{saved_id}?flash=created",
                        status_code=303,
                    )
                return RedirectResponse(
                    url=f"{resource.panel.prefix}/{resource.slug}?flash=created",
                    status_code=303,
                )
            except Exception as exc:
                html = resource.panel._render("form.html", {
                    "resource": resource,
                    "record": data,
                    "record_id": None,
                    "errors": {"__all__": str(exc)},
                }, user=user)
                return HTMLResponse(html, status_code=422)

        # ---- GET /resource/options ---- JSON list for BelongsTo selectors -
        # Registered BEFORE /{record_id} so the literal "options" path
        # doesn't get captured as a primary key value.
        @router.get(f"{prefix}/options", response_model=None, include_in_schema=False)
        async def options_endpoint(
            request: Request, q: str | None = None
        ) -> JSONResponse:
            if await resource.panel._require_login(request):
                return JSONResponse([], status_code=401)
            try:
                data = await resource.get_options(q=q)
            except Exception:
                data = []
            return JSONResponse(data)

        # ---- GET /resource/{id}/view ---- read-only detail page --------
        @router.get(f"{prefix}/{{record_id}}/view", response_class=HTMLResponse, response_model=None, include_in_schema=False)
        async def detail_view(
            record_id: str, request: Request, flash: str | None = None
        ) -> HTMLResponse | RedirectResponse:
            if (redir := await resource.panel._require_login(request)):
                return redir
            if not resource.can_view:
                return await resource.panel._render_error(403, "Access Denied", "Viewing records is not allowed for this resource.", request=request)
            if not await resource._user_allowed(request, "view"):
                return await resource.panel._render_error(403, "Access Denied", "You don't have permission to view this record.", request=request)
            user = await resource.panel._current_user(request)
            try:
                record = await resource.get_record(record_id)
                if record is None:
                    return await resource.panel._render_error(404, "Not Found", "The record you're looking for doesn't exist.", request=request)
            except NotImplementedError:
                return await resource.panel._render_error(501, "Not Supported", "This resource does not support a detail view.", request=request)
            html = resource.panel._render("detail.html", {
                "resource": resource,
                "record": record,
                "record_id": record_id,
                "flash": flash,
            }, user=user)
            return HTMLResponse(html)

        # ---- GET /resource/{id} ---- populated edit form -------------
        @router.get(f"{prefix}/{{record_id}}", response_class=HTMLResponse, response_model=None, include_in_schema=False)
        async def edit_form_view(
            record_id: str, request: Request, flash: str | None = None
        ) -> HTMLResponse | RedirectResponse:
            if (redir := await resource.panel._require_login(request)):
                return redir
            if not resource.can_edit:
                return await resource.panel._render_error(403, "Access Denied", "Editing records is not allowed for this resource.", request=request)
            if not await resource._user_allowed(request, "edit"):
                return await resource.panel._render_error(403, "Access Denied", "You don't have permission to edit this record.", request=request)
            user = await resource.panel._current_user(request)
            try:
                record = await resource.get_record(record_id)
                if record is None:
                    return await resource.panel._render_error(404, "Not Found", "The record you're looking for doesn't exist.", request=request)
            except NotImplementedError:
                record = None
            html = resource.panel._render("form.html", {
                "resource": resource,
                "record": record,
                "record_id": record_id,
                "errors": {},
                "flash": flash,
            }, user=user)
            return HTMLResponse(html)

        # ---- POST /resource/{id} ---- handle update ------------------
        @router.post(f"{prefix}/{{record_id}}", response_class=HTMLResponse, response_model=None, include_in_schema=False)
        async def edit_submit(record_id: str, request: Request) -> HTMLResponse | RedirectResponse:
            if (redir := await resource.panel._require_login(request)):
                return redir
            if not resource.can_edit:
                return await resource.panel._render_error(403, "Access Denied", "Editing records is not allowed for this resource.", request=request)
            if not await resource._user_allowed(request, "edit"):
                return await resource.panel._render_error(403, "Access Denied", "You don't have permission to edit this record.", request=request)
            user = await resource.panel._current_user(request)
            data = await resource.parse_form(request)
            # Server-side validation
            errors = resource._validate_fields(resource._flat_form_fields, data)
            if errors:
                html = resource.panel._render("form.html", {
                    "resource": resource,
                    "record": data,
                    "record_id": record_id,
                    "errors": errors,
                    "flash": None,
                }, user=user)
                return HTMLResponse(html, status_code=422)
            action = (await request.form()).get("_action", "save")
            try:
                await resource.save_record(record_id, data)
                await resource.after_save(record_id, data)
                if action == "save_and_continue":
                    return RedirectResponse(
                        url=f"{resource.panel.prefix}/{resource.slug}/{record_id}?flash=saved",
                        status_code=303,
                    )
                return RedirectResponse(
                    url=f"{resource.panel.prefix}/{resource.slug}?flash=saved",
                    status_code=303,
                )
            except Exception as exc:
                html = resource.panel._render("form.html", {
                    "resource": resource,
                    "record": data,
                    "record_id": record_id,
                    "errors": {"__all__": str(exc)},
                }, user=user)
                return HTMLResponse(html, status_code=422)

        # ---- DELETE /resource/{id} ---- HTMX row delete --------------
        @router.delete(f"{prefix}/{{record_id}}", response_model=None, include_in_schema=False)
        async def delete_view(record_id: str, request: Request) -> HTMLResponse | RedirectResponse:
            if (redir := await resource.panel._require_login(request)):
                return redir
            if not resource.can_delete:
                return await resource.panel._render_error(403, "Access Denied", "Deleting records is not allowed for this resource.", request=request)
            if not await resource._user_allowed(request, "delete"):
                return await resource.panel._render_error(403, "Access Denied", "You don't have permission to delete this record.", request=request)
            try:
                await resource.delete_record(record_id)
                return HTMLResponse("", status_code=200)
            except NotImplementedError:
                return await resource.panel._render_error(501, "Not Supported", "Delete is not implemented for this resource.", request=request)
            except Exception as exc:
                return await resource.panel._render_error(500, "Server Error", "An unexpected error occurred while deleting the record.", request=request)

        # ---- POST /resource/action/{key} ---- list-level action -------
        @router.post(
            f"{prefix}/action/{{action_key}}",
            response_class=HTMLResponse,
            response_model=None,
            include_in_schema=False,
        )
        async def list_action_view(
            action_key: str, request: Request
        ) -> HTMLResponse | RedirectResponse:
            if (redir := await resource.panel._require_login(request)):
                return redir
            if not await resource._user_allowed(request, "action", action_key):
                return await resource.panel._render_error(403, "Access Denied", "You don't have permission to perform this action.", request=request)
            data = await resource.parse_action_form(request)
            # Validate action form fields if present
            action_obj = None
            for lst in (resource.row_actions, resource.list_actions, resource.form_actions):
                for a in lst:
                    if a.key == action_key:
                        action_obj = a
                        break
                if action_obj:
                    break
            if action_obj and getattr(action_obj, "form_fields", None):
                errors = resource._validate_fields(action_obj.form_fields, data)
                if errors:
                    return await resource.panel._render_error(422, "Validation Error", str(errors), request=request)
            try:
                result = await resource._dispatch_action(action_key, None, data, request)
            except (LookupError, NotImplementedError) as exc:
                return await resource.panel._render_error(501, "Not Supported", str(exc), request=request)
            except Exception as exc:
                return await resource.panel._render_error(500, "Server Error", "An unexpected error occurred while running this action.", request=request)
            if isinstance(result, str):
                return RedirectResponse(url=result, status_code=303)
            from fastapi.responses import Response
            if isinstance(result, Response):
                return result
            return RedirectResponse(
                url=f"{resource.panel.prefix}/{resource.slug}?flash=action_ok",
                status_code=303,
            )

        # ---- POST /resource/{id}/action/{key} ---- row / form action ---
        @router.post(
            f"{prefix}/{{record_id}}/action/{{action_key}}",
            response_class=HTMLResponse,
            response_model=None,
            include_in_schema=False,
        )
        async def record_action_view(
            record_id: str, action_key: str, request: Request
        ) -> HTMLResponse | RedirectResponse:
            if (redir := await resource.panel._require_login(request)):
                return redir
            if not await resource._user_allowed(request, "action", action_key):
                return await resource.panel._render_error(403, "Access Denied", "You don't have permission to perform this action.", request=request)
            data = await resource.parse_action_form(request)
            # Validate action form fields if present
            action_obj = None
            for lst in (resource.row_actions, resource.list_actions, resource.form_actions):
                for a in lst:
                    if a.key == action_key:
                        action_obj = a
                        break
                if action_obj:
                    break
            if action_obj and getattr(action_obj, "form_fields", None):
                errors = resource._validate_fields(action_obj.form_fields, data)
                if errors:
                    return await resource.panel._render_error(422, "Validation Error", str(errors), request=request)
            try:
                result = await resource._dispatch_action(
                    action_key, record_id, data, request
                )
            except (LookupError, NotImplementedError) as exc:
                return await resource.panel._render_error(501, "Not Supported", str(exc), request=request)
            except Exception as exc:
                return await resource.panel._render_error(500, "Server Error", "An unexpected error occurred while running this action.", request=request)
            if isinstance(result, str):
                return RedirectResponse(url=result, status_code=303)
            from fastapi.responses import Response
            if isinstance(result, Response):
                return result
            # Choose redirect target based on where the action was triggered.
            referer = request.headers.get("referer", "")
            view_url = f"{resource.panel.prefix}/{resource.slug}/{record_id}/view"
            form_url = f"{resource.panel.prefix}/{resource.slug}/{record_id}"
            if view_url in referer:
                return RedirectResponse(
                    url=f"{view_url}?flash=action_ok", status_code=303
                )
            if form_url in referer:
                return RedirectResponse(
                    url=f"{form_url}?flash=action_ok", status_code=303
                )
            return RedirectResponse(
                url=f"{resource.panel.prefix}/{resource.slug}?flash=action_ok",
                status_code=303,
            )
