from typing import Any
from datetime import date
from sqlalchemy.orm import selectinload

from nuru import forms
from nuru.columns import Text, Badge, Boolean, Image, Currency, DateTime
from nuru.resources.base import Resource
from nuru.forms.base import Form
from nuru.tables.base import Table
from nuru.actions.base import Action

from example_app.models import Checkout, Book, Member
from example_app.db import get_session


class _CheckoutView:
    def __init__(self, co: Checkout, book: Book | None, member: Member | None):
        for attr in ("id", "book_id", "member_id", "issued_on", "due_date",
                     "returned_on", "status", "fine_amount", "fine_paid", "notes"):
            setattr(self, attr, getattr(co, attr))
        self.book   = book
        self.member = member

    def __str__(self) -> str:
        return f"Checkout #{self.id}"


class CheckoutResource(Resource):
    label = "Checkout"
    label_plural = "Checkouts"
    nav_sort = 60
    nav_icon = "calendar"
    model = Checkout
    session_factory = get_session
    search_fields = ["status"]
    form_cols = 2
    load_options = [selectinload(Checkout.book), selectinload(Checkout.member)]

    def table(self) -> Table:
        return Table().schema([
            Text("book.title",   "Book"),
            Text("member.name",  "Member"),
            Text("issued_on",    "Issued",    sortable=True),
            Text("due_date",     "Due date",  sortable=True),
            Badge("status", "Status", colors={
                "issued": "blue", "returned": "green", "overdue": "amber", "lost": "red",
            }),
            Boolean("fine_paid", "Fine paid"),
        ])

    def form(self) -> Form:
        return (
            Form()
            .actions([
                Action.make("mark_returned").label("Mark Returned")
                .handler("mark_returned").placement("header").style("success")
                .confirm("Mark this book as returned?").icon("M5 13l4 4L19 7"),
                Action.make("mark_lost").label("Mark Lost")
                .handler("mark_lost").placement("header").style("danger")
                .fields([
                    forms.Number("fine_amount").label("Loss fine (KES)").required(),
                    forms.Textarea("note").label("Comment").placeholder("e.g. Member reported book lost at home."),
                ]),
                Action.make("add_note").label("Add Note")
                .handler("add_note").placement("inline").style("default")
                .fields([
                    forms.Textarea("note").label("Note").required().placeholder("Visible to staff only..."),
                ]),
            ])
            .schema([
                forms.Section(
                    [
                        forms.Select.make("book_id").label("Book")
                        .model(Book, label_field="title").relationship("book")
                        .required().help_text("Search by title or ISBN.").remote_search(),
                        forms.Select.make("member_id").label("Member")
                        .model(Member, label_field="name").relationship("member")
                        .required().help_text("Search by name or member number.").remote_search(),
                        forms.DatePicker("issued_on").label("Issued on").help_text("Date the book was handed to the member."),
                        forms.DatePicker("due_date").label("Due date").help_text("Expected return date."),
                        forms.DatePicker("returned_on").label("Returned on").help_text("Leave blank if not yet returned."),
                        forms.Select.make("status").label("Status")
                        .options(lambda record=None: [
                            {"value": "issued",   "label": "Issued"},
                            {"value": "returned", "label": "Returned"},
                            {"value": "overdue",  "label": "Overdue"},
                            {"value": "lost",     "label": "Lost"},
                        ])
                        .help_text("Current state of this checkout."),
                    ],
                    title="Checkout Details", cols=2, col_span="full",
                ),
                forms.Section(
                    [
                        forms.Number("fine_amount").label("Fine amount (KES)").help_text("Accumulated overdue or loss penalty."),
                        forms.Checkbox.make("fine_paid").label("Fine paid").help_text("Check once the member has settled the fine."),
                    ],
                    title="Fine", cols=2, col_span="full",
                ),
                forms.Section(
                    [
                        forms.Textarea("notes").label("Staff notes").col_span("full").placeholder("Extension requests, damage notes, etc."),
                    ],
                    title="Notes", col_span="full",
                ),
                forms.Section(
                    [
                        forms.FileUpload("attachment").label("Attachment")
                        .directory("checkouts")
                        .accept_file_types(["application/pdf", "image/jpeg", "image/png"])
                        .max_file_size(10 * 1024 * 1024)
                        .col_span("full")
                        .help_text("Scanned returns slip, damage report, or agreement (PDF/image, max 10 MB). Optional."),
                    ],
                    title="Attachment", col_span="full",
                ),
            ])
        )

    async def get_record(self, id: Any) -> _CheckoutView | None:
        async with get_session() as session:
            co = await session.get(Checkout, int(id))
            if co is None:
                return None
            book   = await session.get(Book,   co.book_id)   if co.book_id   else None
            member = await session.get(Member, co.member_id) if co.member_id else None
            return _CheckoutView(co, book, member)

    async def mark_returned(self, record_id, data, request):
        async with get_session() as session:
            co = await session.get(Checkout, int(record_id))
            if co:
                co.status = "returned"
                co.returned_on = date.today()
                await session.commit()

    async def mark_lost(self, record_id, data, request):
        fine = float(data.get("fine_amount") or 0)
        note = str(data.get("note") or "").strip()
        async with get_session() as session:
            co = await session.get(Checkout, int(record_id))
            if co:
                co.status = "lost"
                co.fine_amount = fine
                if note:
                    co.notes = f"{co.notes or ''}\n{note}".strip()
                await session.commit()

    async def add_note(self, record_id, data, request):
        note = str(data.get("note") or "").strip()
        if not note:
            return
        async with get_session() as session:
            co = await session.get(Checkout, int(record_id))
            if co:
                co.notes = f"{co.notes or ''}\n{note}".strip()
                await session.commit()

