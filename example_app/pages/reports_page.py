from fastapi import Request
from fastapi.responses import RedirectResponse, Response
from datetime import datetime, timezone

from nuru import forms
from nuru.columns import Text, Badge, Boolean, Image, Currency, DateTime
from nuru.pages.base import Page

from example_app.models import Book, Member, Checkout
from example_app.db import get_session

_quick_notes: list[dict] = []


class ReportsPage(Page):
    label = "Reports"
    slug = "reports"
    nav_sort = 100
    nav_icon = "chart-bar"

    async def get_context(self, request: Request) -> dict:
        async with get_session() as session:
            from sqlmodel import select as sm_select
            from sqlalchemy.orm import selectinload
            all_books     = (await session.exec(sm_select(Book))).all()
            all_members   = (await session.exec(sm_select(Member))).all()
            all_checkouts = (await session.exec(
                sm_select(Checkout).options(
                    selectinload(Checkout.book),
                    selectinload(Checkout.member),
                )
            )).all()

        kpi = {
            "total_books":     str(len(all_books)),
            "available_books": str(sum(1 for b in all_books if b.available)),
            "total_members":   str(len(all_members)),
            "active_members":  str(sum(1 for m in all_members if m.active)),
            "issued_now":      str(sum(1 for c in all_checkouts if c.status == "issued")),
            "overdue":         str(sum(1 for c in all_checkouts if c.status == "overdue")),
            "total_fines":     f"{sum(c.fine_amount for c in all_checkouts):,.2f}",
            "unpaid_fines":    f"{sum(c.fine_amount for c in all_checkouts if not c.fine_paid):,.2f}",
        }

        kpi_fields = [
            forms.TextInput.make("total_books").label("Total books"),
            forms.TextInput.make("available_books").label("Currently available"),
            forms.TextInput.make("total_members").label("Registered members"),
            forms.TextInput.make("active_members").label("Active members"),
            forms.TextInput.make("issued_now").label("Books currently out"),
            forms.TextInput.make("overdue").label("Overdue checkouts"),
            forms.TextInput.make("total_fines").label("Total fines (KES)"),
            forms.TextInput.make("unpaid_fines").label("Unpaid fines (KES)"),
        ]

        recent_checkouts = sorted(all_checkouts, key=lambda c: c.id or 0, reverse=True)[:10]

        checkout_columns = [
            Text("id",        "ID",       sortable=True),
            Text("book.title",  "Book"),
            Text("member.name", "Member"),
            Text("issued_on", "Issued"),
            Text("due_date",  "Due"),
            Badge("status", "Status", colors={
                "issued": "blue", "returned": "green", "overdue": "amber", "lost": "red",
            }),
        ]

        note_fields = [
            forms.TextInput("author").label("Your name").required().placeholder("Jane Doe"),
            forms.Textarea("message").label("Note").required().col_span("full")
            .placeholder("Write a quick message for staff..."),
        ]
        note_columns = [
            Text("author",    "Staff member"),
            Text("message",   "Message"),
            Text("posted_at", "Posted at"),
        ]

        return {
            "kpi_fields":       kpi_fields,
            "kpi":              kpi,
            "checkout_columns": checkout_columns,
            "recent_checkouts": recent_checkouts,
            "note_fields":      note_fields,
            "note_columns":     note_columns,
            "notes":            list(_quick_notes),
            "form_error":       request.query_params.get("error", ""),
            "form_success":     request.query_params.get("success", ""),
            "record":           None,
            "errors":           None,
        }

    async def handle_post(self, request: Request) -> Response:
        form    = await request.form()
        author  = str(form.get("author",  "")).strip()
        message = str(form.get("message", "")).strip()
        if not author or not message:
            return RedirectResponse(
                f"{self.panel.prefix}/{self.slug}?error=Please+fill+in+all+fields.",
                status_code=303,
            )
        _quick_notes.insert(0, {
            "author":    author,
            "message":   message,
            "posted_at": datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC"),
        })
        return RedirectResponse(
            f"{self.panel.prefix}/{self.slug}?success=Note+posted.",
            status_code=303,
        )

