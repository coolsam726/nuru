from __future__ import annotations

from typing import Any, ClassVar, Union, get_args, get_origin, TYPE_CHECKING
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

if TYPE_CHECKING:
    from .panel import AdminPanel


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

    table_columns: list = []
    form_fields: list = []
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

    # ------------------------------------------------------------------
    # Internal setup
    # ------------------------------------------------------------------

    def __init__(self, *, panel: AdminPanel) -> None:
        self.panel = panel
        if not self.slug:
            self.slug = self.label.lower().replace(" ", "-")
        if not self.label_plural:
            self.label_plural = self.label + "s"

    # ------------------------------------------------------------------
    # Data hooks — override these in your subclass
    # ------------------------------------------------------------------

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
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement save_record()"
        )

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

        for field in self.form_fields:
            key = field.key
            if field.field_type == "checkbox":
                data[key] = submitted.get(key) == "true"
            elif key in submitted:
                if key.startswith("_"):
                    continue
                value = submitted[key]
                data[key] = value if value != "" else None
            else:
                data[key] = None

        return data

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
            html = resource.panel._render("partials/table.html", ctx)
            return HTMLResponse(html)

        # ---- GET /resource/new ---- blank create form ----------------
        @router.get(f"{prefix}/new", response_class=HTMLResponse, response_model=None, include_in_schema=False)
        async def create_form_view(request: Request) -> HTMLResponse | RedirectResponse:
            if (redir := await resource.panel._require_login(request)):
                return redir
            if not resource.can_create:
                return HTMLResponse("Not allowed", status_code=403)
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
                return HTMLResponse("Not allowed", status_code=403)
            user = await resource.panel._current_user(request)
            data = await resource.parse_form(request)
            action = (await request.form()).get("_action", "save")
            try:
                record = await resource.save_record(None, data)
                saved_id = record["id"] if isinstance(record, dict) else getattr(record, "id", None)
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

        # ---- GET /resource/{id}/view ---- read-only detail page --------
        @router.get(f"{prefix}/{{record_id}}/view", response_class=HTMLResponse, response_model=None, include_in_schema=False)
        async def detail_view(
            record_id: str, request: Request, flash: str | None = None
        ) -> HTMLResponse | RedirectResponse:
            if (redir := await resource.panel._require_login(request)):
                return redir
            if not resource.can_view:
                return HTMLResponse("Not allowed", status_code=403)
            user = await resource.panel._current_user(request)
            try:
                record = await resource.get_record(record_id)
                if record is None:
                    return HTMLResponse("Record not found", status_code=404)
            except NotImplementedError:
                return HTMLResponse("Detail view not supported", status_code=501)
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
                return HTMLResponse("Not allowed", status_code=403)
            user = await resource.panel._current_user(request)
            try:
                record = await resource.get_record(record_id)
                if record is None:
                    return HTMLResponse("Record not found", status_code=404)
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
                return HTMLResponse("Not allowed", status_code=403)
            user = await resource.panel._current_user(request)
            data = await resource.parse_form(request)
            action = (await request.form()).get("_action", "save")
            try:
                await resource.save_record(record_id, data)
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
                return HTMLResponse("Not allowed", status_code=403)
            try:
                await resource.delete_record(record_id)
                return HTMLResponse("", status_code=200)
            except NotImplementedError:
                return HTMLResponse("Delete not implemented", status_code=501)
            except Exception as exc:
                return HTMLResponse(str(exc), status_code=500)

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
            data = await resource.parse_action_form(request)
            try:
                result = await resource._dispatch_action(action_key, None, data, request)
            except (LookupError, NotImplementedError) as exc:
                return HTMLResponse(str(exc), status_code=501)
            except Exception as exc:
                return HTMLResponse(str(exc), status_code=500)
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
            data = await resource.parse_action_form(request)
            try:
                result = await resource._dispatch_action(
                    action_key, record_id, data, request
                )
            except (LookupError, NotImplementedError) as exc:
                return HTMLResponse(str(exc), status_code=501)
            except Exception as exc:
                return HTMLResponse(str(exc), status_code=500)
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
