from nuru import forms
from nuru.columns import Text, Badge, Boolean, Image, Currency, DateTime
from nuru.resources.base import Resource
from nuru.forms.base import Form
from nuru.tables.base import Table
from nuru.infolists.base import Infolist
from nuru.infolists.components import TextEntry, ImageEntry, BooleanEntry, DateEntry

from example_app.models import Author
from example_app.db import get_session


class AuthorResource(Resource):
    label = "Author"
    label_plural = "Authors"
    nav_sort = 20
    nav_icon = "user"
    model = Author
    session_factory = get_session
    search_fields = ["name", "email", "nationality"]
    options_label_field = "name"

    def table(self) -> Table:
        return Table().schema([
            Image("avatar", "Photo", url_prefix="uploads",
                          img_class="size-10 rounded-lg object-cover p-0.5"),
            Text("name",        "Name",        sortable=True),
            Text("nationality", "Nationality", sortable=True),
            Text("email",       "Email"),
            Boolean("active",   "Active"),
        ])

    def form(self) -> Form:
        return Form().schema([
            forms.Section(
                [
                    forms.TextInput.make("name").label("Full name").required().placeholder("e.g. Chinua Achebe"),
                    forms.TextInput.make("email").email().label("Email").placeholder("author@example.com"),
                    forms.TextInput.make("nationality").label("Nationality").placeholder("e.g. Nigerian"),
                    forms.DatePicker("birth_date").label("Date of birth"),
                    forms.Checkbox.make("active").label("Active").help_text("Uncheck to hide from the catalogue."),
                ],
                title="Identity", cols=2, col_span="full",
            ),
            forms.Section(
                [
                    forms.Textarea("bio").label("Short bio").col_span("full")
                    .placeholder("A sentence or two about this author..."),
                ],
                title="Biography", col_span="full",
            ),
            forms.Section(
                [
                    forms.FileUpload("avatar").label("Author photo").image()
                    .directory("authors")
                    .accept_file_types(["image/jpeg", "image/png", "image/webp", "image/svg"])
                    .max_file_size(5 * 1024 * 1024)
                    .image_crop_aspect_ratio("1:1")
                    .col_span("full").input_class("w-20 h-20")
                    .help_text("Square photo works best. Max 5 MB (JPEG, PNG, WebP)."),
                ],
                title="Photo", col_span="full",
            ),
        ])

    def infolist(self) -> Infolist:
        return Infolist().schema([
            forms.Section(
                [
                    ImageEntry.make("avatar").label("Photo")
                    .img_class("size-48 rounded-2xl object-cover")
                    .url_prefix("/admin/uploads").col_span("full"),
                    TextEntry.make("name").label("Full name"),
                    TextEntry.make("email").label("Email"),
                    TextEntry.make("nationality").label("Nationality"),
                    DateEntry.make("birth_date").label("Date of birth"),
                    BooleanEntry.make("active").label("Active"),
                ],
                title="Identity", cols=2, col_span="full",
            ),
            forms.Section(
                [TextEntry.make("bio").label("Biography").col_span("full")],
                title="Biography", col_span="full",
            ),
        ])

