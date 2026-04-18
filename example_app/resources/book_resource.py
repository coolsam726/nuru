from typing import Any
from sqlalchemy.orm import selectinload

from nuru import columns, forms
from nuru.resources.base import Resource
from nuru.forms.base import Form
from nuru.tables.base import Table
from nuru.actions.base import Action
from nuru.forms import Radio, Toggle, TimePicker, RadioButtons

from example_app.models import Book, Author, Subject
from example_app.db import get_session


class _BookView:
    """Wraps a Book with pre-loaded Author and Subject for the detail page."""

    def __init__(self, book: Book, author: Author | None, subject: Subject | None):
        for attr in ("id", "isbn", "title", "author_id", "subject_id",
                     "year", "edition", "copies", "available", "location", "notes"):
            setattr(self, attr, getattr(book, attr))
        self.author  = author
        self.subject = subject

    def __str__(self) -> str:
        return self.title


class BookResource(Resource):
    label = "Book"
    label_plural = "Books"
    slug = "books"
    nav_sort = 40
    nav_icon = "book-open"
    model = Book
    session_factory = get_session
    search_fields = ["isbn", "title", "location"]
    options_label_field = "title"
    form_cols = 2
    load_options = [selectinload(Book.author), selectinload(Book.subject)]

    def table(self) -> Table:
        return Table().schema([
            columns.Text("isbn",         "ISBN",      sortable=True),
            columns.Text("title",        "Title",     sortable=True),
            columns.Text("location",     "Location"),
            columns.Boolean("available", "Available"),
        ])

    def form(self) -> Form:
        return (
            Form()
            .set_actions([
                Action.make("mark_unavailable")
                .label("Mark Unavailable")
                .set_handler("mark_unavailable")
                .set_placement("header")
                .set_style("warning")
                .set_confirm("Mark this book as unavailable for checkout?")
                .set_icon("M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"),
                Action.make("mark_available")
                .label("Mark Available")
                .set_handler("mark_available")
                .set_placement("header")
                .set_style("success")
                .set_confirm("Mark this book as available for checkout?")
                .set_icon("M5 13l4 4L19 7"),
            ])
            .schema([
                forms.Section(
                    [
                        forms.TextInput.make("title").label("Title").required().col_span("full").placeholder("e.g. Things Fall Apart"),
                        forms.TextInput.make("isbn").label("ISBN").required().placeholder("978-..."),
                        forms.Number("year").label("Publication year").placeholder("e.g. 1958"),
                        forms.Select.make("author_id").label("Author")
                        .model(Author, label_field="name").relationship("author")
                        .help_text("Start typing to search authors."),
                        forms.Select.make("subject_id").label("Subject")
                        .model(Subject, label_field="name").relationship("subject")
                        .help_text("The shelf this book belongs to."),
                        forms.TextInput.make("edition").label("Edition").placeholder("e.g. 2nd, Revised"),
                        forms.TextInput.make("location").label("Shelf location").placeholder("e.g. AFL-A1"),
                    ],
                    title="Catalogue Details", cols=2, col_span="full",
                ),
                forms.Section(
                    [
                        forms.Number("copies").label("Number of copies").help_text("Total physical copies held."),
                        forms.Checkbox.make("available").label("Available for checkout")
                        .help_text("Uncheck if all copies are out or the book is being repaired."),
                    ],
                    title="Inventory", cols=2, col_span="full",
                ),
                forms.Section(
                    [
                        forms.Textarea("notes").label("Notes").col_span("full")
                        .placeholder("Condition notes, acquisition info, etc."),
                    ],
                    title="Internal Notes", col_span="full",
                ),
                forms.Section(
                    [
                        Radio("demo_radio").label("Demo radio").options(["Option 1", "Option 2", "Option 3"]),
                        Toggle("demo_toggle").label("Demo toggle").help_text("Just a toggle for demonstration purposes."),
                        TimePicker("demo_timepicker").label("Demo timepicker").help_text("A simple timepicker input."),
                        RadioButtons("demo_radiobuttons").label("Demo radio buttons").options([
                            {"value": "vue",     "label": "Vue.js",   "description": "A progressive JavaScript framework.",                          "image": "https://vuejs.org/images/logo.png"},
                            {"value": "react",   "label": "React",    "description": "A JavaScript library for building user interfaces.",            "image": "https://reactjs.org/logo-og.png"},
                            {"value": "angular", "label": "Angular",  "description": "A platform for building mobile and desktop web applications.",  "image": "https://angular.io/assets/images/logos/angular/angular.png"},
                            {"value": "svelte",  "label": "Svelte",   "description": "Cybernetically enhanced web apps.",                            "image": "https://svelte.dev/svelte-logo-horizontal.svg"},
                        ]).col_span("full"),
                        RadioButtons.make("slim_buttons").options([
                            {"value": "groq_ai", "label": "Groq AI", "icon": "cpu-chip"},
                            {"value": "claude",  "label": "Claude",  "icon": "cpu-chip"},
                            {"value": "gemini",  "label": "Gemini",  "icon": "cpu-chip"},
                            {"value": "gpt",     "label": "GPT",     "icon": "cpu-chip"},
                        ]).label("Slim buttons"),
                    ],
                    title="Extras", cols=2, col_span="full",
                ),
            ])
        )

    async def get_record(self, id: Any) -> _BookView | None:
        async with get_session() as session:
            book = await session.get(Book, int(id))
            if book is None:
                return None
            author  = await session.get(Author,  book.author_id)  if book.author_id  else None
            subject = await session.get(Subject, book.subject_id) if book.subject_id else None
            return _BookView(book, author, subject)

    async def mark_unavailable(self, record_id, data, request):
        async with get_session() as session:
            book = await session.get(Book, int(record_id))
            if book:
                book.available = False
                await session.commit()

    async def mark_available(self, record_id, data, request):
        async with get_session() as session:
            book = await session.get(Book, int(record_id))
            if book:
                book.available = True
                await session.commit()

