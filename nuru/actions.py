from __future__ import annotations

import json
from dataclasses import dataclass, field as dc_field
from .fields import Field

# ---------------------------------------------------------------------------
# Button style → Tailwind class mapping
# ---------------------------------------------------------------------------

_STYLE_CLASSES: dict[str, str] = {
    "default":   ("border border-zinc-200 dark:border-zinc-600 "
                  "text-zinc-700 dark:text-zinc-300 "
                  "hover:bg-zinc-50 dark:hover:bg-zinc-700"),
    "secondary": ("border border-zinc-300 dark:border-zinc-600 "
                  "text-zinc-500 dark:text-zinc-400 "
                  "hover:bg-zinc-50 dark:hover:bg-zinc-700"),
    "primary":   "text-white bg-primary hover:bg-primary-600",
    "success":   ("border border-green-200 dark:border-green-700/50 "
                  "text-green-700 dark:text-green-400 "
                  "hover:bg-green-50 dark:hover:bg-green-900/30"),
    "warning":   ("border border-amber-200 dark:border-amber-700/50 "
                  "text-amber-700 dark:text-amber-400 "
                  "hover:bg-amber-50 dark:hover:bg-amber-900/30"),
    "danger":    ("border border-red-200 dark:border-red-700/50 "
                  "text-red-700 dark:text-red-400 "
                  "hover:bg-red-50 dark:hover:bg-red-900/30"),
}


# ---------------------------------------------------------------------------
# Action — the single action class for all placements
# ---------------------------------------------------------------------------

@dataclass
class Action:
    """
    A server-side action button.  A single ``Action`` class covers every
    placement — row actions in the list table, list-page header actions,
    form-page header actions, and inline actions inside a form card.

    The ``handler`` attribute is the **name of a method on your Resource**
    class.  The framework looks it up and calls it automatically; no
    ``handle_action`` / ``handle_row_action`` dispatch method is needed.

    Usage::

        from nuru.actions import Action
        from nuru import fields

        class UserResource(Resource):

            row_actions = [
                Action("activate",   label="Activate",   handler="activate_user",
                       style="success", icon="M5 13l4 4L19 7"),
                Action("deactivate", label="Deactivate", handler="deactivate_user",
                       style="warning", confirm="Deactivate this user?"),
                Action("reset_pw",   label="Reset PW",   handler="reset_password",
                       style="danger",
                       form_fields=[
                           fields.Password("new_password", "New password", required=True),
                       ]),
            ]

            list_actions = [
                Action("export_csv", label="Export CSV", handler="do_export",
                       style="secondary"),
                Action("notify_all", label="Notify All", handler="send_notification",
                       style="warning",
                       form_fields=[
                           fields.Text("subject", "Subject",  required=True),
                           fields.Textarea("body", "Message"),
                       ]),
            ]

            form_actions = [
                Action("refund",   label="Issue Refund", handler="refund_order",
                       placement="header", style="danger",
                       form_fields=[
                           fields.Number("amount", "Amount",  required=True),
                           fields.Textarea("reason", "Reason"),
                       ]),
                Action("add_note", label="Add Note",     handler="add_order_note",
                       placement="inline", style="default",
                       form_fields=[
                           fields.Textarea("note", "Note", required=True),
                       ]),
            ]

            # ── Handler methods ────────────────────────────────────────────
            # Signature: async def <name>(self, record_id, data, request)
            #   record_id — primary-key string, or None for list-level actions
            #   data      — dict of fields collected by the modal (empty if none)
            #   request   — FastAPI Request
            # Return None to use the default redirect, or a URL string to
            # redirect to a custom location.

            async def activate_user(self, record_id, data, request):
                user = next(u for u in _users if str(u["id"]) == str(record_id))
                user["active"] = True

            async def deactivate_user(self, record_id, data, request):
                user = next(u for u in _users if str(u["id"]) == str(record_id))
                user["active"] = False

            async def reset_password(self, record_id, data, request):
                await user_service.set_password(record_id, data["new_password"])

            async def do_export(self, record_id, data, request):
                # record_id is None for list-level actions
                ...  # return a StreamingResponse or None

            async def send_notification(self, record_id, data, request):
                await mailer.send(data["subject"], data["body"])

            async def refund_order(self, record_id, data, request):
                await payments.refund(record_id, amount=data["amount"],
                                      reason=data.get("reason", ""))

            async def add_order_note(self, record_id, data, request):
                await notes.create(order_id=record_id, text=data["note"])

    Attributes:
        key:        Unique identifier used in the action URL.  Must be unique
                    across *all* action lists on a Resource.
        label:      Button label text.
        handler:    **Name of a method on the Resource** to invoke when the
                    action fires.  The method receives
                    ``(self, record_id, data, request)`` and may be async.
        style:      Visual style — ``"default"`` | ``"secondary"`` |
                    ``"primary"`` | ``"success"`` | ``"warning"`` | ``"danger"``.
        placement:  Where the button appears **within a form page** —
                    ``"header"`` (topbar, right side) or ``"inline"`` (form
                    card footer beside Save).  Does not apply to ``row_actions``
                    or ``list_actions``.
        confirm:    Plain-text confirmation message shown in a browser dialog
                    before submitting when ``form_fields`` is empty.
        form_fields: If non-empty, clicking the button opens a modal that
                    collects data before submitting to the handler.
                    Pass any :mod:`nuru.fields` instance — ``Text``,
                    ``Textarea``, ``Select``, ``Checkbox``, ``Number``, etc.
        form_title: Modal dialog heading; defaults to ``label``.
        icon:       Optional SVG ``path d="…"`` string rendered as a 4×4
                    leading icon inside the button.
    """

    key: str
    label: str
    handler: str                                          # method name on the Resource
    style: str = "default"
    placement: str = "header"                             # header | inline (form_actions only)
    confirm: str | None = None
    form_fields: list[Field] = dc_field(default_factory=list)
    form_title: str = ""
    icon: str = ""
    is_builtin: bool = False                              # always False for user-defined actions

    # ── Helpers called by Jinja2 templates ────────────────────────────

    @property
    def modal_title(self) -> str:
        return self.form_title or self.label

    @property
    def button_class(self) -> str:
        return _STYLE_CLASSES.get(self.style, _STYLE_CLASSES["default"])

    def fields_json(self) -> str:
        """JSON-serialise ``form_fields`` for the ``data-action-fields`` HTML attribute."""
        result = []
        for f in self.form_fields:
            d: dict = {
                "key":        f.get_key(),
                "label":      f.get_label(),
                "field_type": f.get_field_type(),
                "input_type": f.get_input_type(),
                "required":   f.is_required(),
                "placeholder": f.get_placeholder(),
                "help_text":  f.get_help_text(),
                "options":    [],
            }
            if hasattr(f, "get_options"):
                opts = f.get_options()
                if callable(opts):
                    opts = []
                d["options"] = opts
            result.append(d)
        return json.dumps(result)
