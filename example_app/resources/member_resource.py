from typing import Any

from nuru import columns, forms
from nuru.resources.base import Resource
from nuru.forms.base import Form
from nuru.tables.base import Table
from nuru.infolists.base import Infolist
from nuru.infolists.components import TextEntry, ImageEntry, BooleanEntry, BadgeEntry, DateEntry
from nuru.actions.base import Action

from example_app.models import Member
from example_app.db import get_session


class MemberResource(Resource):
    label = "Member"
    label_plural = "Members"
    slug = "members"
    nav_sort = 50
    nav_icon = "users"
    model = Member
    session_factory = get_session
    search_fields = ["name", "email", "member_number"]
    options_label_field = "name"

    def table(self) -> Table:
        return (
            Table()
            .schema([
                columns.Text("member_number", "Number",  sortable=True),
                columns.Text("name",          "Name",    sortable=True),
                columns.Text("email",         "Email"),
                columns.Badge("membership", "Type", colors={
                    "standard": "blue", "student": "amber",
                    "senior": "green",  "staff":   "purple",
                }),
                columns.Boolean("active", "Active"),
            ])
            .set_row_actions([
                Action.make("suspend").label("Suspend")
                .set_handler("suspend_member").set_style("danger")
                .set_confirm("Suspend this member's account?")
                .set_icon("M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"),
                Action.make("reactivate").label("Reactivate")
                .set_handler("reactivate_member").set_style("success")
                .set_icon("M5 13l4 4L19 7"),
            ])
        )

    def form(self) -> Form:
        return Form().schema([
            forms.Section(
                [
                    forms.TextInput.make("name").label("Full name").required().placeholder("Jane Doe"),
                    forms.TextInput.make("email").email().label("Email address").required(),
                    forms.TextInput.make("phone").label("Phone number").placeholder("+254 700 000 000"),
                    forms.DatePicker("joined_on").label("Joined on"),
                ],
                title="Personal Details", cols=2, col_span="full",
            ),
            forms.Section(
                [
                    forms.TextInput.make("member_number").label("Member number").required().placeholder("MBR-001").help_text("Unique ID printed on the member card."),
                    forms.Select.make("membership").label("Membership type").options(["standard", "student", "senior", "staff"]).help_text("Determines checkout limits and fee waivers."),
                    forms.Checkbox.make("active").label("Active").help_text("Inactive members cannot borrow books."),
                ],
                title="Membership", cols=2, col_span="full",
            ),
            forms.Section(
                [
                    forms.Textarea("notes").label("Staff notes").col_span("full").placeholder("Special instructions, suspension reasons, etc."),
                ],
                title="Notes", col_span="full",
            ),
            forms.Section(
                [
                    forms.FileUpload("avatar").label("Member photo / ID scan").image()
                    .directory("members")
                    .accept_file_types(["image/jpeg", "image/png", "image/webp"])
                    .max_file_size(5 * 1024 * 1024)
                    .image_crop_aspect_ratio("1:1")
                    .col_span("full")
                    .help_text("Passport photo or scanned ID. Max 5 MB."),
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
                    TextEntry.make("phone").label("Phone"),
                    DateEntry.make("joined_on").label("Joined on"),
                ],
                title="Personal Details", cols=2, col_span="full",
            ),
            forms.Section(
                [
                    TextEntry.make("member_number").label("Member number"),
                    BadgeEntry.make("membership").label("Type").colors({
                        "standard": "blue", "student": "amber",
                        "senior":   "green", "staff":  "purple",
                    }),
                    BooleanEntry.make("active").label("Active"),
                ],
                title="Membership", cols=2, col_span="full",
            ),
            forms.Section(
                [TextEntry.make("notes").label("Staff notes").col_span("full")],
                title="Notes", col_span="full",
            ),
        ])

    async def suspend_member(self, record_id, data, request):
        async with get_session() as session:
            m = await session.get(Member, int(record_id))
            if m:
                m.active = False
                await session.commit()

    async def reactivate_member(self, record_id, data, request):
        async with get_session() as session:
            m = await session.get(Member, int(record_id))
            if m:
                m.active = True
                await session.commit()

