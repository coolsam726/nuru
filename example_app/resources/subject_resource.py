from nuru import columns, forms
from nuru.resources.base import Resource
from nuru.forms.base import Form
from nuru.tables.base import Table

from example_app.models import Subject
from example_app.db import get_session


class SubjectResource(Resource):
    label = "Subject"
    label_plural = "Subjects"
    nav_sort = 30
    nav_icon = "bookmark"
    model = Subject
    session_factory = get_session
    search_fields = ["name", "code"]
    options_label_field = "name"

    def table(self) -> Table:
        return Table().schema([
            columns.Text("code",      "Code",    sortable=True),
            columns.Text("name",      "Subject", sortable=True),
            columns.Text("floor",     "Floor"),
            columns.Boolean("active", "Active"),
        ])

    def form(self) -> Form:
        return Form().schema([
            forms.Section(
                [
                    forms.TextInput.make("name").label("Subject name").required().placeholder("e.g. African Literature"),
                    forms.TextInput.make("code").label("Short code").required().placeholder("e.g. AFL").help_text("Used for shelf labels."),
                    forms.Select.make("floor").label("Library floor")
                    .options(lambda record=None: [
                        {"value": "G",        "label": "Ground (G)"},
                        {"value": "1st",      "label": "First (1st)"},
                        {"value": "2nd",      "label": "Second (2nd)"},
                        {"value": "3rd",      "label": "Third (3rd)"},
                        {"value": "Basement", "label": "Basement"},
                    ])
                    .help_text("Physical floor in the building."),
                    forms.Checkbox.make("active").label("Active").help_text("Inactive subjects are hidden from the public catalogue."),
                    forms.Textarea("description").label("Description").col_span("full").placeholder("What kinds of books live here?"),
                ],
                title="Shelf Details", cols=2, col_span="full",
            ),
        ])

