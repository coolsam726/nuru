"""
Nuru example app — Kibrary Library Management System
=====================================================

Demonstrates every field type and the model-based relationship Select field.

Run with:  uvicorn example_app.main:app --reload

  /admin  — auth-protected  (user: admin@kibrary.org / pass: secret)

Models
------
  StaffUser   — panel login accounts
  Author      — book authors           (demonstrates: Text, Email, Textarea, Date)
  Subject     — subjects / "shelves"   (demonstrates: Text, Select, Checkbox)
  Book        — library catalogue      (demonstrates: Text, Number, Select[model],
                                        Select, Checkbox, Textarea)
  Member      — library members        (demonstrates: Text, Email, Tel, Date,
                                        Select, Checkbox, Textarea)
  Checkout    — issued / returned      (demonstrates: Select[model] x2, Date, Select,
                                        Checkbox, Textarea, Number)
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional
from datetime import date

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from sqlmodel import SQLModel, Relationship, Field as SMField, select as sm_select
from sqlmodel.ext.asyncio.session import AsyncSession as _AsyncSession
from sqlalchemy.ext.asyncio import (
    create_async_engine as _cae,
    async_sessionmaker as _asm,
)

from nuru.components import (
    register_components,
    Timepicker,
    Radio,
    Toggle,
    RadioButtons,
)
from nuru.components.types import RadioOption
from nuru.integrations.flowbite import register_flowbite
import nuru.roles
from nuru import (
    AdminPanel,
    Page,
    Resource,
    DatabaseAuthBackend,
    db_permission_checker,
    Permission,
    Role,
    RolePermission,
    UserRole,
    columns,
    fields,
    forms,
)
from sqlalchemy.orm import selectinload
from nuru.actions import Action

# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

_engine = _cae("sqlite+aiosqlite:///example_db.sqlite3")
_SessionFactory = _asm(_engine, class_=_AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def _get_session():
    async with _SessionFactory() as session:
        yield session


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class StaffUser(SQLModel, table=True):
    __tablename__ = "staff_users"
    id: Optional[int] = SMField(default=None, primary_key=True)
    name: str
    email: str
    password: Optional[str] = None
    role: str = "librarian"
    active: bool = True

    def __str__(self) -> str:
        return self.name


class Author(SQLModel, table=True):
    __tablename__ = "authors"
    id: Optional[int] = SMField(default=None, primary_key=True)
    name: str
    email: Optional[str] = None
    nationality: Optional[str] = None
    birth_date: Optional[date] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None   # FilePond server ID (relative path under uploads/)
    active: bool = True
    books: list["Book"] = Relationship(
        back_populates="author"
    )  # for back_populates in Book.author_id

    def __str__(self) -> str:
        return self.name


class Subject(SQLModel, table=True):
    __tablename__ = "subjects"
    id: Optional[int] = SMField(default=None, primary_key=True)
    name: str
    code: str
    description: Optional[str] = None
    floor: Optional[str] = None
    active: bool = True

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class Book(SQLModel, table=True):
    __tablename__ = "books"
    id: Optional[int] = SMField(default=None, primary_key=True)
    isbn: str
    title: str
    author_id: Optional[int] = SMField(default=None, foreign_key="authors.id")
    subject_id: Optional[int] = SMField(default=None, foreign_key="subjects.id")
    year: Optional[int] = None
    edition: Optional[str] = None
    copies: int = 1
    available: bool = True
    location: Optional[str] = None
    notes: Optional[str] = None

    author: Optional[Author] = Relationship(back_populates="books")
    subject: Optional["Subject"] = Relationship()

    def __str__(self) -> str:
        return self.title


class Member(SQLModel, table=True):
    __tablename__ = "members"
    id: Optional[int] = SMField(default=None, primary_key=True)
    name: str
    email: str
    phone: Optional[str] = None
    member_number: str
    membership: str = "standard"
    joined_on: Optional[date] = None
    active: bool = True
    notes: Optional[str] = None
    avatar: Optional[str] = None   # FilePond server ID (relative path under uploads/)
    checkouts: list["Checkout"] = Relationship(
        back_populates="member"
    )  # for back_populates in Checkout.member_id

    def __str__(self) -> str:
        return f"{self.name} ({self.member_number})"


class Checkout(SQLModel, table=True):
    __tablename__ = "checkouts"
    id: Optional[int] = SMField(default=None, primary_key=True)
    book_id: Optional[int] = SMField(default=None, foreign_key="books.id")
    member_id: Optional[int] = SMField(default=None, foreign_key="members.id")
    book: Optional[Book] = Relationship()
    member: Optional[Member] = Relationship(back_populates="checkouts")
    issued_on: Optional[date] = None
    due_date: Optional[date] = None
    returned_on: Optional[date] = None
    status: str = "issued"
    fine_amount: float = 0.0
    fine_paid: bool = False
    notes: Optional[str] = None
    attachment: Optional[str] = None  # FilePond server ID — e.g. a scanned returns slip

    def __str__(self) -> str:
        return f"Checkout #{self.id}"


# ---------------------------------------------------------------------------
# Lifespan — schema sync + seed data
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _lifespan(app: FastAPI):
    from nuru.migrations import sync_schema

    await sync_schema(_engine, SQLModel.metadata)
    await admin_panel.sync_permissions(_get_session)

    async with _get_session() as session:

        # ── Roles ────────────────────────────────────────────────────
        if not (await session.exec(sm_select(Role))).first():
            super_admin = Role(name="Super Admin", description="Full access")
            librarian = Role(name="Librarian", description="Manage books and checkouts")
            read_only = Role(name="Read Only", description="View-only access")
            session.add_all([super_admin, librarian, read_only])
            await session.flush()

            star_perm = (
                await session.exec(
                    sm_select(Permission).where(Permission.codename == "*")
                )
            ).first()
            if star_perm:
                session.add(
                    RolePermission(role_id=super_admin.id, permission_id=star_perm.id)
                )

            lib_codenames = [
                "author:list",
                "author:view",
                "author:create",
                "author:edit",
                "subject:list",
                "subject:view",
                "subject:create",
                "subject:edit",
                "book:list",
                "book:view",
                "book:create",
                "book:edit",
                "book:action",
                "member:list",
                "member:view",
                "member:create",
                "member:edit",
                "member:action",
                "checkout:list",
                "checkout:view",
                "checkout:create",
                "checkout:edit",
                "checkout:action",
            ]
            lib_perms = (
                await session.exec(
                    sm_select(Permission).where(Permission.codename.in_(lib_codenames))
                )
            ).all()
            for p in lib_perms:
                session.add(RolePermission(role_id=librarian.id, permission_id=p.id))

            view_codenames = [
                "author:list",
                "author:view",
                "subject:list",
                "subject:view",
                "book:list",
                "book:view",
                "member:list",
                "member:view",
                "checkout:list",
                "checkout:view",
            ]
            view_perms = (
                await session.exec(
                    sm_select(Permission).where(Permission.codename.in_(view_codenames))
                )
            ).all()
            for p in view_perms:
                session.add(RolePermission(role_id=read_only.id, permission_id=p.id))

            await session.commit()

        # ── Staff users ───────────────────────────────────────────────
        if not (await session.exec(sm_select(StaffUser))).first():
            admin_user = StaffUser(
                name="Admin User",
                email="admin@kibrary.org",
                password="secret",
                role="admin",
                active=True,
            )
            lib_user = StaffUser(
                name="Jane Librarian",
                email="jane@kibrary.org",
                password="librarian123",
                role="librarian",
                active=True,
            )
            viewer_user = StaffUser(
                name="Viewer User",
                email="viewer@kibrary.org",
                password="viewer123",
                role="viewer",
                active=True,
            )
            session.add_all([admin_user, lib_user, viewer_user])
            await session.flush()

            super_admin = (
                await session.exec(sm_select(Role).where(Role.name == "Super Admin"))
            ).first()
            librarian = (
                await session.exec(sm_select(Role).where(Role.name == "Librarian"))
            ).first()
            read_only = (
                await session.exec(sm_select(Role).where(Role.name == "Read Only"))
            ).first()
            if super_admin:
                session.add(
                    UserRole(user_id=str(admin_user.id), role_id=super_admin.id)
                )
            if librarian:
                session.add(UserRole(user_id=str(lib_user.id), role_id=librarian.id))
            if read_only:
                session.add(UserRole(user_id=str(viewer_user.id), role_id=read_only.id))
            await session.commit()

        # ── Authors ───────────────────────────────────────────────────
        if not (await session.exec(sm_select(Author))).first():
            session.add_all(
                [
                    Author(
                        name="Chinua Achebe",
                        email="c.achebe@example.com",
                        nationality="Nigerian",
                        birth_date=date(1930, 11, 16),
                        bio="Renowned Nigerian novelist and poet.",
                        active=True,
                    ),
                    Author(
                        name="Ngugi wa Thiongo",
                        email="ngugi@example.com",
                        nationality="Kenyan",
                        birth_date=date(1938, 1, 5),
                        bio="Leading voice of African literature.",
                        active=True,
                    ),
                    Author(
                        name="Wole Soyinka",
                        email="soyinka@example.com",
                        nationality="Nigerian",
                        birth_date=date(1934, 7, 13),
                        bio="Nobel laureate — literary and dramatic work.",
                        active=True,
                    ),
                    Author(
                        name="Chimamanda Adichie",
                        email="adichie@example.com",
                        nationality="Nigerian",
                        birth_date=date(1977, 9, 15),
                        bio="Author of Half of a Yellow Sun.",
                        active=True,
                    ),
                    Author(
                        name="Binyavanga Wainaina",
                        email="binyavanga@example.com",
                        nationality="Kenyan",
                        birth_date=date(1971, 1, 18),
                        bio="Journalist and memoirist.",
                        active=False,
                    ),
                    Author(
                        name="Ama Ata Aidoo",
                        email="aidoo@example.com",
                        nationality="Ghanaian",
                        birth_date=date(1942, 3, 23),
                        bio="Pioneer of African feminist literature.",
                        active=True,
                    ),
                    Author(
                        name="George Orwell",
                        email=None,
                        nationality="British",
                        birth_date=date(1903, 6, 25),
                        bio="Author of 1984 and Animal Farm.",
                        active=True,
                    ),
                    Author(
                        name="Gabriel Garcia Marquez",
                        email=None,
                        nationality="Colombian",
                        birth_date=date(1927, 3, 6),
                        bio="Nobel laureate — magical realism.",
                        active=True,
                    ),
                ]
            )
            await session.commit()

        # ── Subjects ──────────────────────────────────────────────────
        if not (await session.exec(sm_select(Subject))).first():
            session.add_all(
                [
                    Subject(
                        name="African Literature",
                        code="AFL",
                        description="Fiction and non-fiction from African writers.",
                        floor="1st",
                        active=True,
                    ),
                    Subject(
                        name="Science Fiction",
                        code="SCI",
                        description="Speculative and science fiction.",
                        floor="2nd",
                        active=True,
                    ),
                    Subject(
                        name="History",
                        code="HIS",
                        description="World and regional history.",
                        floor="2nd",
                        active=True,
                    ),
                    Subject(
                        name="Philosophy",
                        code="PHI",
                        description="Classics and contemporary philosophy.",
                        floor="3rd",
                        active=True,
                    ),
                    Subject(
                        name="Children",
                        code="CHI",
                        description="Picture books, early readers, middle grade.",
                        floor="G",
                        active=True,
                    ),
                    Subject(
                        name="Reference",
                        code="REF",
                        description="Encyclopaedias, dictionaries, atlases.",
                        floor="G",
                        active=True,
                    ),
                    Subject(
                        name="Self Help",
                        code="SLF",
                        description="Personal development and wellness.",
                        floor="1st",
                        active=True,
                    ),
                    Subject(
                        name="Periodicals",
                        code="PER",
                        description="Journals, magazines, and newspapers.",
                        floor="G",
                        active=False,
                    ),
                ]
            )
            await session.commit()

        # ── Books ─────────────────────────────────────────────────────
        if not (await session.exec(sm_select(Book))).first():
            authors = {
                a.name: a.id for a in (await session.exec(sm_select(Author))).all()
            }
            subjects = {
                s.code: s.id for s in (await session.exec(sm_select(Subject))).all()
            }
            session.add_all(
                [
                    Book(
                        isbn="978-0435905255",
                        title="Things Fall Apart",
                        author_id=authors.get("Chinua Achebe"),
                        subject_id=subjects.get("AFL"),
                        year=1958,
                        edition="1st",
                        copies=4,
                        available=True,
                        location="AFL-A1",
                        notes="Classic post-colonial novel.",
                    ),
                    Book(
                        isbn="978-0435905897",
                        title="No Longer at Ease",
                        author_id=authors.get("Chinua Achebe"),
                        subject_id=subjects.get("AFL"),
                        year=1960,
                        edition="1st",
                        copies=2,
                        available=True,
                        location="AFL-A1",
                    ),
                    Book(
                        isbn="978-0143039020",
                        title="A Grain of Wheat",
                        author_id=authors.get("Ngugi wa Thiongo"),
                        subject_id=subjects.get("AFL"),
                        year=1967,
                        edition="2nd",
                        copies=3,
                        available=True,
                        location="AFL-N1",
                    ),
                    Book(
                        isbn="978-0143039044",
                        title="Petals of Blood",
                        author_id=authors.get("Ngugi wa Thiongo"),
                        subject_id=subjects.get("AFL"),
                        year=1977,
                        edition="1st",
                        copies=2,
                        available=False,
                        location="AFL-N1",
                        notes="Currently under repair.",
                    ),
                    Book(
                        isbn="978-0062301697",
                        title="Half of a Yellow Sun",
                        author_id=authors.get("Chimamanda Adichie"),
                        subject_id=subjects.get("AFL"),
                        year=2006,
                        edition="1st",
                        copies=5,
                        available=True,
                        location="AFL-C1",
                    ),
                    Book(
                        isbn="978-0307455925",
                        title="Americanah",
                        author_id=authors.get("Chimamanda Adichie"),
                        subject_id=subjects.get("AFL"),
                        year=2013,
                        edition="1st",
                        copies=3,
                        available=True,
                        location="AFL-C1",
                    ),
                    Book(
                        isbn="978-0451524935",
                        title="1984",
                        author_id=authors.get("George Orwell"),
                        subject_id=subjects.get("SCI"),
                        year=1949,
                        edition="Signet",
                        copies=6,
                        available=True,
                        location="SCI-O1",
                        notes="Perennial bestseller.",
                    ),
                    Book(
                        isbn="978-0060964344",
                        title="One Hundred Years of Solitude",
                        author_id=authors.get("Gabriel Garcia Marquez"),
                        subject_id=subjects.get("AFL"),
                        year=1967,
                        edition="1st Eng",
                        copies=3,
                        available=True,
                        location="AFL-G1",
                    ),
                    Book(
                        isbn="978-0140441185",
                        title="The Analects",
                        author_id=None,
                        subject_id=subjects.get("PHI"),
                        year=479,
                        edition="Penguin",
                        copies=2,
                        available=True,
                        location="PHI-P1",
                    ),
                    Book(
                        isbn="978-0143105954",
                        title="Weep Not Child",
                        author_id=authors.get("Ngugi wa Thiongo"),
                        subject_id=subjects.get("AFL"),
                        year=1964,
                        edition="1st",
                        copies=2,
                        available=True,
                        location="AFL-N2",
                    ),
                    Book(
                        isbn="978-0521898423",
                        title="Death and the Kings Horseman",
                        author_id=authors.get("Wole Soyinka"),
                        subject_id=subjects.get("AFL"),
                        year=1975,
                        edition="Cambridge",
                        copies=2,
                        available=True,
                        location="AFL-S1",
                    ),
                    Book(
                        isbn="978-0141182803",
                        title="Animal Farm",
                        author_id=authors.get("George Orwell"),
                        subject_id=subjects.get("SCI"),
                        year=1945,
                        edition="Penguin",
                        copies=5,
                        available=True,
                        location="SCI-O2",
                    ),
                    *[
                        Book(
                            isbn=f"978-000000{100 + i:04d}",
                            title=f"Library Acquisition {i}",
                            author_id=None,
                            subject_id=subjects.get("REF"),
                            year=2020 + (i % 5),
                            copies=1,
                            available=i % 3 != 0,
                            location=f"REF-{i:03d}",
                        )
                        for i in range(1, 21)
                    ],
                ]
            )
            await session.commit()

        # ── Members ───────────────────────────────────────────────────
        if not (await session.exec(sm_select(Member))).first():
            session.add_all(
                [
                    Member(
                        name="Amina Hassan",
                        email="amina@email.com",
                        phone="+254701000001",
                        member_number="MBR-001",
                        membership="standard",
                        joined_on=date(2022, 1, 15),
                        active=True,
                    ),
                    Member(
                        name="Baraka Ochieng",
                        email="baraka@email.com",
                        phone="+254701000002",
                        member_number="MBR-002",
                        membership="student",
                        joined_on=date(2022, 3, 10),
                        active=True,
                    ),
                    Member(
                        name="Cynthia Waweru",
                        email="cynthia@email.com",
                        phone="+254701000003",
                        member_number="MBR-003",
                        membership="senior",
                        joined_on=date(2021, 6, 20),
                        active=True,
                    ),
                    Member(
                        name="Danstan Mwenda",
                        email="danstan@email.com",
                        phone="+254701000004",
                        member_number="MBR-004",
                        membership="standard",
                        joined_on=date(2023, 2, 5),
                        active=True,
                    ),
                    Member(
                        name="Edith Ajuma",
                        email="edith@email.com",
                        phone="+254701000005",
                        member_number="MBR-005",
                        membership="staff",
                        joined_on=date(2020, 9, 1),
                        active=True,
                    ),
                    Member(
                        name="Francis Njoroge",
                        email="francis@email.com",
                        phone="+254701000006",
                        member_number="MBR-006",
                        membership="student",
                        joined_on=date(2023, 8, 22),
                        active=True,
                    ),
                    Member(
                        name="Grace Mutua",
                        email="grace@email.com",
                        phone="+254701000007",
                        member_number="MBR-007",
                        membership="standard",
                        joined_on=date(2022, 11, 30),
                        active=False,
                        notes="Account suspended — pending renewal.",
                    ),
                    Member(
                        name="Hassan Abdi",
                        email="hassan@email.com",
                        phone="+254701000008",
                        member_number="MBR-008",
                        membership="senior",
                        joined_on=date(2019, 4, 17),
                        active=True,
                    ),
                    Member(
                        name="Irene Chebet",
                        email="irene@email.com",
                        phone="+254701000009",
                        member_number="MBR-009",
                        membership="student",
                        joined_on=date(2024, 1, 8),
                        active=True,
                    ),
                    Member(
                        name="James Kipchoge",
                        email="james@email.com",
                        phone="+254701000010",
                        member_number="MBR-010",
                        membership="standard",
                        joined_on=date(2021, 7, 14),
                        active=True,
                    ),
                    *[
                        Member(
                            name=f"Member {i}",
                            email=f"member{i}@email.com",
                            member_number=f"MBR-{100 + i:03d}",
                            membership="standard",
                            joined_on=date(2023, 1, 1),
                            active=True,
                        )
                        for i in range(1, 21)
                    ],
                ]
            )
            await session.commit()

        # ── Checkouts ─────────────────────────────────────────────────
        if not (await session.exec(sm_select(Checkout))).first():
            books = {b.title: b.id for b in (await session.exec(sm_select(Book))).all()}
            members = {
                m.name: m.id for m in (await session.exec(sm_select(Member))).all()
            }
            session.add_all(
                [
                    Checkout(
                        book_id=books.get("Things Fall Apart"),
                        member_id=members.get("Amina Hassan"),
                        issued_on=date(2025, 1, 5),
                        due_date=date(2025, 1, 19),
                        returned_on=date(2025, 1, 18),
                        status="returned",
                        fine_amount=0.0,
                        fine_paid=False,
                    ),
                    Checkout(
                        book_id=books.get("1984"),
                        member_id=members.get("Baraka Ochieng"),
                        issued_on=date(2025, 2, 10),
                        due_date=date(2025, 2, 24),
                        returned_on=None,
                        status="issued",
                        fine_amount=0.0,
                        fine_paid=False,
                        notes="Member requested extension.",
                    ),
                    Checkout(
                        book_id=books.get("Half of a Yellow Sun"),
                        member_id=members.get("Cynthia Waweru"),
                        issued_on=date(2024, 12, 1),
                        due_date=date(2024, 12, 15),
                        returned_on=None,
                        status="overdue",
                        fine_amount=150.0,
                        fine_paid=False,
                        notes="Reminder SMS sent.",
                    ),
                    Checkout(
                        book_id=books.get("Americanah"),
                        member_id=members.get("Danstan Mwenda"),
                        issued_on=date(2025, 3, 1),
                        due_date=date(2025, 3, 15),
                        returned_on=date(2025, 3, 14),
                        status="returned",
                        fine_amount=0.0,
                        fine_paid=False,
                    ),
                    Checkout(
                        book_id=books.get("A Grain of Wheat"),
                        member_id=members.get("Edith Ajuma"),
                        issued_on=date(2025, 3, 20),
                        due_date=date(2025, 4, 3),
                        returned_on=None,
                        status="issued",
                        fine_amount=0.0,
                        fine_paid=False,
                    ),
                    Checkout(
                        book_id=books.get("Animal Farm"),
                        member_id=members.get("Francis Njoroge"),
                        issued_on=date(2025, 1, 20),
                        due_date=date(2025, 2, 3),
                        returned_on=None,
                        status="overdue",
                        fine_amount=300.0,
                        fine_paid=True,
                        notes="Fine paid at counter.",
                    ),
                    Checkout(
                        book_id=books.get("One Hundred Years of Solitude"),
                        member_id=members.get("Hassan Abdi"),
                        issued_on=date(2025, 3, 5),
                        due_date=date(2025, 3, 19),
                        returned_on=date(2025, 3, 19),
                        status="returned",
                        fine_amount=0.0,
                        fine_paid=False,
                    ),
                    Checkout(
                        book_id=books.get("Death and the Kings Horseman"),
                        member_id=members.get("Irene Chebet"),
                        issued_on=date(2025, 4, 1),
                        due_date=date(2025, 4, 15),
                        returned_on=None,
                        status="issued",
                        fine_amount=0.0,
                        fine_paid=False,
                    ),
                    Checkout(
                        book_id=books.get("No Longer at Ease"),
                        member_id=members.get("James Kipchoge"),
                        issued_on=date(2025, 2, 1),
                        due_date=date(2025, 2, 15),
                        returned_on=None,
                        status="lost",
                        fine_amount=500.0,
                        fine_paid=False,
                        notes="Member reported book lost.",
                    ),
                    Checkout(
                        book_id=books.get("1984"),
                        member_id=members.get("Amina Hassan"),
                        issued_on=date(2025, 4, 5),
                        due_date=date(2025, 4, 19),
                        returned_on=None,
                        status="issued",
                        fine_amount=0.0,
                        fine_paid=False,
                    ),
                ]
            )
            await session.commit()

    yield


app = FastAPI(title="Kibrary — Nuru Library Demo", lifespan=_lifespan)


# ===========================================================================
# Resource: Author
# Demonstrates: Text, Email, Date, Textarea, Checkbox
# ===========================================================================


class AuthorResource(Resource):
    label = "Author"
    label_plural = "Authors"
    nav_sort = 20
    nav_icon = "user"
    model = Author
    session_factory = _get_session
    search_fields = ["name", "email", "nationality"]
    options_label_field = "name"

    table_columns = [
        columns.Text("name", "Name", sortable=True),
        columns.Text("nationality", "Nationality", sortable=True),
        columns.Text("email", "Email"),
        columns.Boolean("active", "Active"),
    ]

    form_fields = [
        forms.Section(
            [
                forms.TextInput
                .make("name")
                .label("Full name")
                .required()
                .placeholder("e.g. Chinua Achebe"),
                forms.TextInput.make("email")
                .email()
                .label("Email")
                .required()
                .placeholder("author@example.com"),
                forms.TextInput.make("nationality")
                .label("Nationality")
                .placeholder("e.g. Nigerian"),
                forms.DatePicker("birth_date").label("Date of birth"),
                forms.Checkbox.make("active")
                .label("Active")
                .help_text("Uncheck to hide from the catalogue."),
            ],
            title="Identity",
            cols=2,
            col_span="full",
        ),
        forms.Section(
            [
                forms.Textarea("bio")
                .label("Short bio")
                .col_span("full")
                .placeholder("A sentence or two about this author..."),
            ],
            title="Biography",
            col_span="full",
        ),
        forms.Section(
            [
                forms.FileUpload("avatar")
                .label("Author photo")
                .image()
                .directory("authors")
                .accept_file_types(["image/jpeg", "image/png", "image/webp"])
                .max_file_size(5 * 1024 * 1024)
                .image_crop_aspect_ratio("1:1")
                .col_span("full")
                .help_text("Square photo works best. Max 5 MB (JPEG, PNG, WebP)."),
            ],
            title="Photo",
            col_span="full",
        ),
    ]

    detail_fields = [
        forms.Section(
            [
                forms.TextInput.make("name").label("Full name"),
                forms.TextInput.make("email").email().label("Email"),
                forms.TextInput.make("nationality").label("Nationality"),
                forms.DatePicker("birth_date").label("Date of birth"),
                forms.Checkbox.make("active").label("Active"),
            ],
            title="Identity",
            cols=2,
            col_span="full",
        ),
        forms.Section(
            [
                forms.Textarea("bio").label("Biography").col_span("full"),
            ],
            title="Biography",
            col_span="full",
        ),
    ]


# ===========================================================================
# Resource: Subject
# Demonstrates: Text, Select, Checkbox
# ===========================================================================


class SubjectResource(Resource):
    label = "Subject"
    label_plural = "Subjects"
    nav_sort = 30
    nav_icon = "bookmark"
    model = Subject
    session_factory = _get_session
    search_fields = ["name", "code"]
    options_label_field = "name"

    table_columns = [
        columns.Text("code", "Code", sortable=True),
        columns.Text("name", "Subject", sortable=True),
        columns.Text("floor", "Floor"),
        columns.Boolean("active", "Active"),
    ]

    form_fields = [
        forms.Section(
            [
                forms.TextInput.make("name")
                .label("Subject name")
                .required()
                .placeholder("e.g. African Literature"),
                forms.TextInput.make("code")
                .label("Short code")
                .required()
                .placeholder("e.g. AFL")
                .help_text("Used for shelf labels."),
                forms.Select.make("floor")
                .label("Library floor")
                .options(lambda record: [
                    {"value": f"G", "label": "Ground (G)"},
                    {"value": f"1st", "label": "First (1st)"},
                    {"value": f"2nd", "label": "Second (2nd)"},
                    {"value": f"3rd", "label": "Third (3rd)"},
                    {"value": f"Basement", "label": "Basement"},
                ])
                .help_text("Physical floor in the building."),
                forms.Checkbox.make("active")
                .label("Active")
                .help_text("Inactive subjects are hidden from the public catalogue."),
                forms.Textarea("description")
                .label("Description")
                .col_span("full")
                .placeholder("What kinds of books live here?"),
            ],
            title="Shelf Details",
            cols=2,
            col_span="full",
        ),
    ]

    detail_fields = [
        forms.Section(
            [
                forms.TextInput.make("name").label("Subject name"),
                forms.TextInput.make("code").label("Short code"),
                forms.Select.make("floor")
                .label("Library floor")
                .options(["G", "1st", "2nd", "3rd", "Basement"]),
                forms.Checkbox.make("active").label("Active"),
                forms.Textarea("description").label("Description").col_span("full"),
            ],
            title="Shelf Details",
            cols=2,
            col_span="full",
        ),
    ]


# ===========================================================================
# Resource: Book
# Demonstrates: Select[model] (Author, Subject), Text, Number, Select,
#               Checkbox, Textarea, form_actions
# ===========================================================================


class _BookView:
    """Wraps a Book with pre-loaded Author and Subject for the detail page."""

    def __init__(self, book: Book, author: Author | None, subject: Subject | None):
        for attr in (
                "id",
                "isbn",
                "title",
                "author_id",
                "subject_id",
                "year",
                "edition",
                "copies",
                "available",
                "location",
                "notes",
        ):
            setattr(self, attr, getattr(book, attr))
        self.author = author
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
    session_factory = _get_session
    search_fields = ["isbn", "title", "location"]
    options_label_field = "title"
    form_cols = 2
    load_options = [selectinload(Book.author), selectinload(Book.subject)]

    table_columns = [
        columns.Text("isbn", "ISBN", sortable=True),
        columns.Text("title", "Title", sortable=True),
        columns.Text("location", "Location"),
        columns.Boolean("available", "Available"),
    ]

    form_fields = [
        forms.Section(
            [
                forms.TextInput.make("title")
                .label("Title")
                .required()
                .col_span("full")
                .placeholder("e.g. Things Fall Apart"),
                forms.Text.make("isbn")
                .label("ISBN")
                .required()
                .placeholder("978-..."),
                forms.Number("year")
                .label("Publication year")
                .placeholder("e.g. 1958"),
                forms.Select.make("author_id")
                .label("Author")
                .model(Author, label_field="name")
                .relationship("author")
                .help_text("Start typing to search authors."),
                forms.Select.make("subject_id")
                .label("Subject")
                .model(Subject, label_field="name")
                .relationship("subject")
                .help_text("The shelf this book belongs to."),
                forms.TextInput.make("edition")
                .label("Edition")
                .placeholder("e.g. 2nd, Revised"),
                forms.TextInput.make("location")
                .label("Shelf location")
                .placeholder("e.g. AFL-A1"),
            ],
            title="Catalogue Details",
            cols=2,
            col_span="full",
        ),
        forms.Section(
            [
                forms.Number("copies")
                .label("Number of copies")
                .help_text("Total physical copies held."),
                forms.Checkbox.make("available")
                .label("Available for checkout")
                .help_text(
                    "Uncheck if all copies are out or the book is being repaired."
                ),
            ],
            title="Inventory",
            cols=2,
            col_span="full",
        ),
        forms.Section(
            [
                forms.Textarea("notes")
                .label("Notes")
                .col_span("full")
                .placeholder("Condition notes, acquisition info, etc."),
            ],
            title="Internal Notes",
            col_span="full",
        ),
        forms.Section(
            [
                # Demo the use of the new fields
                Radio("demo_radio")
                .label("Demo radio")
                .options(["Option 1", "Option 2", "Option 3"]),
                Toggle("demo_toggle")
                .label("Demo toggle")
                .help_text("Just a toggle for demonstration purposes."),
                Timepicker("demo_timepicker")
                .label("Demo timepicker")
                .help_text("A simple timepicker input."),
                RadioButtons("demo_radiobuttons")
                .label("Demo radio buttons")
                .options(
                    [
                        {
                            "value": "vue",
                            "label": "Vue.js",
                            "description": "A progressive JavaScript framework.",
                            "image": "https://vuejs.org/images/logo.png",
                        },
                        {
                            "value": "react",
                            "label": "React",
                            "description": "A JavaScript library for building user interfaces.",
                            "image": "https://reactjs.org/logo-og.png",
                        },
                        {
                            "value": "angular",
                            "label": "Angular",
                            "description": "A platform for building mobile and desktop web applications.",
                            "image": "https://angular.io/assets/images/logos/angular/angular.png",
                        },
                        {
                            "value": "svelte",
                            "label": "Svelte",
                            "description": "Cybernetically enhanced web apps.",
                            "image": "https://svelte.dev/svelte-logo-horizontal.svg",
                        },
                    ]
                )
                .col_span("full"),
            ],
            title="Extras",
            cols=2,
            col_span="full",
        ),
    ]

    detail_fields = [
        forms.Section(
            [
                forms.TextInput.make("title").label("Title"),
                forms.TextInput.make("isbn").label("ISBN"),
                forms.Number("year").label("Publication year"),
                forms.Select.make("author_id")
                .label("Author")
                .model(Author, label_field="name")
                .relationship("author"),
                forms.Select.make("subject_id")
                .label("Subject")
                .model(Subject, label_field="name")
                .relationship("subject"),
                forms.TextInput.make("edition").label("Edition"),
                forms.TextInput.make("location").label("Shelf location"),
            ],
            title="Catalogue Details",
            cols=2,
            col_span="full",
        ),
        forms.Section(
            [
                forms.Number("copies").label("Copies"),
                forms.Checkbox.make("available").label("Available"),
            ],
            title="Inventory",
            cols=2,
            col_span="full",
        ),
        forms.Section(
            [
                forms.Textarea("notes").label("Notes").col_span("full"),
            ],
            title="Notes",
            col_span="full",
        ),
    ]

    form_actions = [
        Action(
            "mark_unavailable",
            label="Mark Unavailable",
            handler="mark_unavailable",
            placement="header",
            style="warning",
            confirm="Mark this book as unavailable for checkout?",
            icon="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636",
        ),
        Action(
            "mark_available",
            label="Mark Available",
            handler="mark_available",
            placement="header",
            style="success",
            confirm="Mark this book as available for checkout?",
            icon="M5 13l4 4L19 7",
        ),
    ]

    async def get_record(self, id: Any) -> _BookView | None:
        async with _get_session() as session:
            book = await session.get(Book, int(id))
            if book is None:
                return None
            author = (
                await session.get(Author, book.author_id) if book.author_id else None
            )
            subject = (
                await session.get(Subject, book.subject_id) if book.subject_id else None
            )
            return _BookView(book, author, subject)

    async def mark_unavailable(self, record_id, data, request):
        async with _get_session() as session:
            book = await session.get(Book, int(record_id))
            if book:
                book.available = False
                await session.commit()

    async def mark_available(self, record_id, data, request):
        async with _get_session() as session:
            book = await session.get(Book, int(record_id))
            if book:
                book.available = True
                await session.commit()


# ===========================================================================
# Resource: Member
# Demonstrates: Text, Email, Tel, Date, Select, Checkbox, Textarea, row_actions
# ===========================================================================


class MemberResource(Resource):
    label = "Member"
    label_plural = "Members"
    slug = "members"
    nav_sort = 50
    nav_icon = "users"
    model = Member
    session_factory = _get_session
    search_fields = ["name", "email", "member_number"]
    options_label_field = "name"

    row_actions = [
        Action(
            "suspend",
            label="Suspend",
            handler="suspend_member",
            style="danger",
            confirm="Suspend this member's account?",
            icon="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636",
        ),
        Action(
            "reactivate",
            label="Reactivate",
            handler="reactivate_member",
            style="success",
            icon="M5 13l4 4L19 7",
        ),
    ]

    table_columns = [
        columns.Text("member_number", "Number", sortable=True),
        columns.Text("name", "Name", sortable=True),
        columns.Text("email", "Email"),
        columns.Badge(
            "membership",
            "Type",
            colors={
                "standard": "blue",
                "student": "amber",
                "senior": "green",
                "staff": "purple",
            },
        ),
        columns.Boolean("active", "Active"),
    ]

    form_fields = [
        forms.Section(
            [
                forms.TextInput.make("name")
                .label("Full name")
                .required()
                .placeholder("Jane Doe"),
                forms.TextInput.make("email").email().label("Email address").required(),
                forms.TextInput.make("phone")
                .label("Phone number")
                .placeholder("+254 700 000 000"),
                forms.DatePicker("joined_on").label("Joined on"),
            ],
            title="Personal Details",
            cols=2,
            col_span="full",
        ),
        forms.Section(
            [
                forms.TextInput.make("member_number")
                .label("Member number")
                .required()
                .placeholder("MBR-001")
                .help_text("Unique ID printed on the member card."),
                forms.Select.make("membership")
                .label("Membership type")
                .options(["standard", "student", "senior", "staff"])
                .help_text("Determines checkout limits and fee waivers."),
                forms.Checkbox.make("active")
                .label("Active")
                .help_text("Inactive members cannot borrow books."),
            ],
            title="Membership",
            cols=2,
            col_span="full",
        ),
        forms.Section(
            [
                forms.Textarea("notes")
                .label("Staff notes")
                .col_span("full")
                .placeholder("Special instructions, suspension reasons, etc."),
            ],
            title="Notes",
            col_span="full",
        ),
        forms.Section(
            [
                forms.FileUpload("avatar")
                .label("Member photo / ID scan")
                .image()
                .directory("members")
                .accept_file_types(["image/jpeg", "image/png", "image/webp"])
                .max_file_size(5 * 1024 * 1024)
                .image_crop_aspect_ratio("1:1")
                .col_span("full")
                .help_text("Passport photo or scanned ID. Max 5 MB."),
            ],
            title="Photo",
            col_span="full",
        ),
    ]

    detail_fields = [
        forms.Section(
            [
                forms.TextInput.make("name").label("Full name"),
                forms.TextInput.make("email").email().label("Email"),
                forms.TextInput.make("phone").label("Phone"),
                forms.DatePicker("joined_on").label("Joined on"),
            ],
            title="Personal Details",
            cols=2,
            col_span="full",
        ),
        forms.Section(
            [
                forms.TextInput.make("member_number").label("Member number"),
                forms.Select.make("membership")
                .label("Type")
                .options(["standard", "student", "senior", "staff"]),
                forms.Checkbox.make("active").label("Active"),
            ],
            title="Membership",
            cols=2,
            col_span="full",
        ),
        forms.Section(
            [
                forms.Textarea("notes").label("Staff notes").col_span("full"),
            ],
            title="Notes",
            col_span="full",
        ),
    ]

    async def suspend_member(self, record_id, data, request):
        async with _get_session() as session:
            m = await session.get(Member, int(record_id))
            if m:
                m.active = False
                await session.commit()

    async def reactivate_member(self, record_id, data, request):
        async with _get_session() as session:
            m = await session.get(Member, int(record_id))
            if m:
                m.active = True
                await session.commit()


# ===========================================================================
# Resource: Checkout
# Demonstrates: Select[model] x2 (Book, Member), Date, Select, Checkbox, Number,
#               Textarea, form_actions (inline + header, with form_fields)
# ===========================================================================


class _CheckoutView:
    def __init__(self, co: Checkout, book: Book | None, member: Member | None):
        for attr in (
                "id",
                "book_id",
                "member_id",
                "issued_on",
                "due_date",
                "returned_on",
                "status",
                "fine_amount",
                "fine_paid",
                "notes",
        ):
            setattr(self, attr, getattr(co, attr))
        self.book = book
        self.member = member

    def __str__(self) -> str:
        return f"Checkout #{self.id}"


class CheckoutResource(Resource):
    label = "Checkout"
    label_plural = "Checkouts"
    nav_sort = 60
    nav_icon = "calendar"
    model = Checkout
    session_factory = _get_session
    search_fields = ["status"]
    form_cols = 2
    load_options = [selectinload(Checkout.book), selectinload(Checkout.member)]

    table_columns = [
        columns.Text("book.title", "Book"),
        columns.Text("member.name", "Member"),
        columns.Text("issued_on", "Issued", sortable=True),
        columns.Text("due_date", "Due date", sortable=True),
        columns.Badge(
            "status",
            "Status",
            colors={
                "issued": "blue",
                "returned": "green",
                "overdue": "amber",
                "lost": "red",
            },
        ),
        columns.Boolean("fine_paid", "Fine paid"),
    ]

    form_fields = [
        forms.Section(
            [
                forms.Select.make("book_id")
                .label("Book")
                .model(Book, label_field="title")
                .relationship("book")
                .required()
                .help_text("Search by title or ISBN.")
                .remote_search(),
                forms.Select.make("member_id")
                .label("Member")
                .model(Member, label_field="name")
                .relationship("member")
                .required()
                .help_text("Search by name or member number.")
                .remote_search(),
                forms.DatePicker("issued_on")
                .label("Issued on")
                .help_text("Date the book was handed to the member."),
                forms.DatePicker("due_date")
                .label("Due date")
                .help_text("Expected return date."),
                forms.DatePicker("returned_on")
                .label("Returned on")
                .help_text("Leave blank if not yet returned."),
                forms.Select.make("status")
                .label("Status")
                .options(
                    lambda record=None: [
                        {"value": "issued", "label": "Issued"},
                        {"value": "returned", "label": "Returned"},
                        {"value": "overdue", "label": "Overdue"},
                        {"value": "lost", "label": "Lost"},
                    ]
                )
                .help_text("Current state of this checkout."),
            ],
            title="Checkout Details",
            cols=2,
            col_span="full",
        ),
        forms.Section(
            [
                forms.Number("fine_amount")
                .label("Fine amount (KES)")
                .help_text("Accumulated overdue or loss penalty."),
                forms.Checkbox.make("fine_paid")
                .label("Fine paid")
                .help_text("Check once the member has settled the fine."),
            ],
            title="Fine",
            cols=2,
            col_span="full",
        ),
        forms.Section(
            [
                forms.Textarea("notes")
                .label("Staff notes")
                .col_span("full")
                .placeholder("Extension requests, damage notes, etc."),
            ],
            title="Notes",
            col_span="full",
        ),
        forms.Section(
            [
                forms.FileUpload("attachment")
                .label("Attachment")
                .directory("checkouts")
                .accept_file_types(["application/pdf", "image/jpeg", "image/png"])
                .max_file_size(10 * 1024 * 1024)
                .col_span("full")
                .help_text("Attach a scanned returns slip, damage report, or agreement (PDF/image, max 10 MB). Optional."),
            ],
            title="Attachment",
            col_span="full",
        ),
    ]

    detail_fields = [
        forms.Section(
            [
                forms.Select.make("book_id")
                .label("Book")
                .model(Book, label_field="title")
                .relationship("book"),
                forms.Select.make("member_id")
                .label("Member")
                .model(Member, label_field="name")
                .relationship("member"),
                forms.DatePicker("issued_on").label("Issued on"),
                forms.DatePicker("due_date").label("Due date"),
                forms.DatePicker("returned_on").label("Returned on"),
                forms.Select.make("status")
                .label("Status")
                .options(["issued", "returned", "overdue", "lost"]),
            ],
            title="Checkout Details",
            cols=2,
            col_span="full",
        ),
        forms.Section(
            [
                forms.Number("fine_amount").label("Fine (KES)"),
                forms.Checkbox.make("fine_paid").label("Fine paid"),
            ],
            title="Fine",
            cols=2,
            col_span="full",
        ),
        forms.Section(
            [
                forms.Textarea("notes").label("Staff notes").col_span("full"),
            ],
            title="Notes",
            col_span="full",
        ),
    ]

    form_actions = [
        Action(
            "mark_returned",
            label="Mark Returned",
            handler="mark_returned",
            placement="header",
            style="success",
            confirm="Mark this book as returned?",
            icon="M5 13l4 4L19 7",
        ),
        Action(
            "mark_lost",
            label="Mark Lost",
            handler="mark_lost",
            placement="header",
            style="danger",
            form_fields=[
                forms.Number("fine_amount").label("Loss fine (KES)").required(),
                forms.Textarea("note")
                .label("Comment")
                .placeholder("e.g. Member reported book lost at home."),
            ],
        ),
        Action(
            "add_note",
            label="Add Note",
            handler="add_note",
            placement="inline",
            style="default",
            form_fields=[
                forms.Textarea("note")
                .label("Note")
                .required()
                .placeholder("Visible to staff only..."),
            ],
        ),
    ]

    async def get_record(self, id: Any) -> _CheckoutView | None:
        async with _get_session() as session:
            co = await session.get(Checkout, int(id))
            if co is None:
                return None
            book = await session.get(Book, co.book_id) if co.book_id else None
            member = await session.get(Member, co.member_id) if co.member_id else None
            return _CheckoutView(co, book, member)

    async def mark_returned(self, record_id, data, request):
        from datetime import date as _date

        async with _get_session() as session:
            co = await session.get(Checkout, int(record_id))
            if co:
                co.status = "returned"
                co.returned_on = _date.today()
                await session.commit()

    async def mark_lost(self, record_id, data, request):
        fine = float(data.get("fine_amount") or 0)
        note = str(data.get("note") or "").strip()
        async with _get_session() as session:
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
        async with _get_session() as session:
            co = await session.get(Checkout, int(record_id))
            if co:
                co.notes = f"{co.notes or ''}\n{note}".strip()
                await session.commit()


# ===========================================================================
# Resource: StaffUser
# Demonstrates: Text, Email, Password, Select, Checkbox, CheckboxGroup
# ===========================================================================


class _StaffUserView:
    def __init__(
            self,
            user: StaffUser,
            role_ids: list[str],
            roles_list: list[str],
            all_roles: list[dict],
    ):
        for attr in ("id", "name", "email", "password", "role", "active"):
            setattr(self, attr, getattr(user, attr))
        self.role_ids = role_ids
        self.roles_list = roles_list
        self.all_roles = all_roles

    def __str__(self) -> str:
        return self.name


class StaffUserResource(Resource):
    label = "Staff User"
    label_plural = "Staff Users"
    nav_sort = 70
    nav_icon = "shield-check"
    model = StaffUser
    session_factory = _get_session
    search_fields = ["name", "email"]
    form_cols = 2

    table_columns = [
        columns.Text("name", "Name", sortable=True),
        columns.Text("email", "Email"),
        columns.Badge(
            "role",
            "Display Role",
            colors={
                "admin": "purple",
                "librarian": "blue",
                "viewer": "gray",
            },
        ),
        columns.Boolean("active", "Active"),
    ]

    form_fields = [
        forms.Section(
            [
                forms.TextInput.make("name").label("Full name").required(),
                forms.TextInput.make("email").email().label("Email address").required(),
                forms.Password("password")
                .label("Password")
                .help_text("Leave blank to keep current password."),
                forms.Select.make("role")
                .label("Display role")
                .options(["admin", "librarian", "viewer"])
                .help_text("Badge only — actual access controlled via Roles below."),
                forms.Checkbox.make("active").label("Active"),
            ],
            title="Account",
            cols=2,
            col_span="full",
        ),
        forms.Fieldset(
            [
                forms.CheckboxGroup("role_ids")
                .label("")
                .options_from("all_roles")
                .col_span("full"),
            ],
            title="Assigned Roles",
            description="Grant this user role-based permissions.",
            col_span="full",
            cols=1,
        ),
    ]

    detail_fields = [
        forms.Fieldset(
            [
                forms.TextInput.make("name").label("Full name"),
                forms.Email("email")
                .label("Email"),
                forms.Select.make("role")
                .label("Display role")
                .options(["admin", "librarian", "viewer"]),
                forms.Checkbox.make("active").label("Active"),
            ],
            title="Account",
            cols=2,
        ),
        forms.Fieldset(
            [
                forms.CheckboxGroup("roles_list")
                .label("Roles")
                .options_from("all_roles")
                .col_span("full"),
            ],
            title="Roles",
            col_span="full",
            cols=1,
            description="Roles currently assigned to this user.",
        ),
    ]

    async def get_record(self, id: Any) -> _StaffUserView | None:
        async with _get_session() as session:
            user = await session.get(StaffUser, int(id))
            if user is None:
                return None
            all_roles_rows = (await session.exec(sm_select(Role))).all()
            all_roles = [
                {"value": str(r.id), "label": r.name}
                for r in sorted(all_roles_rows, key=lambda r: r.name)
            ]
            user_roles = (
                await session.exec(
                    sm_select(UserRole).where(UserRole.user_id == str(user.id))
                )
            ).all()
            assigned_ids = [str(ur.role_id) for ur in user_roles]
            role_names = [r.name for r in all_roles_rows if str(r.id) in assigned_ids]
            roles_list = sorted(role_names)
            return _StaffUserView(user, assigned_ids, roles_list, all_roles)

    async def after_save(self, record_id: Any, data: dict) -> None:
        selected_ids = {int(v) for v in (data.get("role_ids") or []) if v}
        async with _get_session() as session:
            user_id = str(record_id)
            existing = (
                await session.exec(
                    sm_select(UserRole).where(UserRole.user_id == user_id)
                )
            ).all()
            existing_ids = {ur.role_id for ur in existing}
            for role_id in selected_ids - existing_ids:
                session.add(UserRole(user_id=user_id, role_id=role_id))
            for ur in existing:
                if ur.role_id not in selected_ids:
                    await session.delete(ur)
            await session.commit()


# ===========================================================================
# Resource: Role
# Demonstrates: Text, CheckboxGroup (permissions M2M)
# ===========================================================================


class _RoleView:
    def __init__(self, role: Role, codenames: list[str], all_perms: list[dict]):
        for attr in ("id", "name", "description"):
            setattr(self, attr, getattr(role, attr))
        self.permission_ids = [p["value"] for p in all_perms if p["label"] in codenames]
        self.all_permissions = all_perms
        self.permissions_list = sorted(codenames)

    def __str__(self) -> str:
        return self.name


class RoleResource(Resource):
    label = "Role"
    label_plural = "Roles"
    nav_sort = 80
    nav_icon = "lock-closed"
    model = Role
    session_factory = _get_session
    search_fields = ["name", "description"]

    table_columns = [
        columns.Text("name", "Role Name", sortable=True),
        columns.Text("description", "Description"),
    ]

    form_fields = [
        forms.Section(
            [
                forms.TextInput.make("name")
                .label("Role name")
                .required()
                .placeholder("e.g. Librarian"),
                forms.TextInput.make("description")
                .label("Description")
                .placeholder("What this role can do"),
            ],
            title="Role",
            cols=2,
            col_span="full",
        ),
        forms.Fieldset(
            [
                forms.CheckboxGroup("permission_ids")
                .label("")
                .options_from("all_permissions")
                .col_span("full"),
            ],
            title="Permissions",
            description="Permissions granted to members of this role. The * wildcard grants everything.",
            col_span="full",
            cols=1,
        ),
    ]

    detail_fields = [
        forms.Fieldset(
            [
                forms.TextInput.make("name").label("Role name"),
                forms.TextInput.make("description").label("Description"),
            ],
            title="Role",
            cols=2,
        ),
        forms.Fieldset(
            [
                forms.CheckboxGroup("permissions_list")
                .label("Permissions")
                .options_from("all_permissions")
                .col_span("full"),
            ],
            title="Permissions",
            col_span="full",
            cols=1,
            description="Codenames granted to users in this role.",
        ),
    ]

    async def get_record(self, id: Any) -> _RoleView | None:
        async with _get_session() as session:
            role = await session.get(Role, int(id))
            if role is None:
                return None
            all_perms_rows = (await session.exec(sm_select(Permission))).all()
            all_perms = [
                {"value": str(p.id), "label": p.codename}
                for p in sorted(all_perms_rows, key=lambda p: p.codename)
            ]
            role_perms = (
                await session.exec(
                    sm_select(RolePermission).where(RolePermission.role_id == role.id)
                )
            ).all()
            assigned_ids = {rp.permission_id for rp in role_perms}
            codenames = [p.codename for p in all_perms_rows if p.id in assigned_ids]
            return _RoleView(role, codenames, all_perms)

    async def after_save(self, record_id: Any, data: dict) -> None:
        selected_ids = {int(v) for v in (data.get("permission_ids") or []) if v}
        async with _get_session() as session:
            role_id = int(record_id)
            existing = (
                await session.exec(
                    sm_select(RolePermission).where(RolePermission.role_id == role_id)
                )
            ).all()
            existing_ids = {rp.permission_id for rp in existing}
            # Preserve wildcard — cannot be removed through the UI.
            if existing_ids:
                wildcard_perms = (
                    await session.exec(
                        sm_select(Permission).where(
                            Permission.id.in_(existing_ids),
                            Permission.codename == "*",
                        )
                    )
                ).all()
                for wp in wildcard_perms:
                    selected_ids.add(wp.id)
            for perm_id in selected_ids - existing_ids:
                session.add(RolePermission(role_id=role_id, permission_id=perm_id))
            for rp in existing:
                if rp.permission_id not in selected_ids:
                    await session.delete(rp)
            await session.commit()


# ===========================================================================
# Page: Reports  (library statistics + quick-notes board)
# ===========================================================================

_EXAMPLE_TEMPLATES = Path(__file__).parent / "templates"
_quick_notes: list[dict] = []


class ReportsPage(Page):
    label = "Reports"
    slug = "reports"
    nav_sort = 100
    nav_icon = "chart-bar"

    async def get_context(self, request: Request) -> dict:
        async with _get_session() as session:
            all_books = (await session.exec(sm_select(Book))).all()
            all_members = (await session.exec(sm_select(Member))).all()
            all_checkouts = (await session.exec(sm_select(Checkout))).all()

        kpi = {
            "total_books": str(len(all_books)),
            "available_books": str(sum(1 for b in all_books if b.available)),
            "total_members": str(len(all_members)),
            "active_members": str(sum(1 for m in all_members if m.active)),
            "issued_now": str(sum(1 for c in all_checkouts if c.status == "issued")),
            "overdue": str(sum(1 for c in all_checkouts if c.status == "overdue")),
            "total_fines": f"{sum(c.fine_amount for c in all_checkouts):,.2f}",
            "unpaid_fines": f"{sum(c.fine_amount for c in all_checkouts if not c.fine_paid):,.2f}",
        }

        kpi_fields = [
            forms.TextInput.make("total_books", "Books in catalogue"),
            forms.TextInput.make("available_books", "Currently available"),
            forms.TextInput.make("total_members", "Registered members"),
            forms.TextInput.make("active_members", "Active members"),
            forms.TextInput.make("issued_now", "Books currently out"),
            forms.TextInput.make("overdue", "Overdue checkouts"),
            forms.TextInput.make("total_fines", "Total fines (KES)"),
            forms.TextInput.make("unpaid_fines", "Unpaid fines (KES)"),
        ]

        recent_checkouts = sorted(all_checkouts, key=lambda c: c.id or 0, reverse=True)[
            :10
        ]

        checkout_columns = [
            columns.Text("id", "ID", sortable=True),
            columns.Text("book_id", "Book ID"),
            columns.Text("member_id", "Member ID"),
            columns.Text("issued_on", "Issued"),
            columns.Text("due_date", "Due"),
            columns.Badge(
                "status",
                "Status",
                colors={
                    "issued": "blue",
                    "returned": "green",
                    "overdue": "amber",
                    "lost": "red",
                },
            ),
        ]

        note_fields = [
            forms.TextInput.make("author", "Your name", required=True, placeholder="Jane Doe"),
            forms.Textarea(
                "message",
                "Note",
                required=True,
                col_span="full",
                placeholder="Write a quick message for staff...",
            ),
        ]
        note_columns = [
            columns.Text("author", "Staff member"),
            columns.Text("message", "Message"),
            columns.Text("posted_at", "Posted at"),
        ]

        return {
            "kpi_fields": kpi_fields,
            "kpi": kpi,
            "checkout_columns": checkout_columns,
            "recent_checkouts": recent_checkouts,
            "note_fields": note_fields,
            "note_columns": note_columns,
            "notes": list(_quick_notes),
            "form_error": request.query_params.get("error", ""),
            "form_success": request.query_params.get("success", ""),
            "record": None,
            "errors": None,
        }

    async def handle_post(self, request: Request) -> Response:
        form = await request.form()
        author = str(form.get("author", "")).strip()
        message = str(form.get("message", "")).strip()
        if not author or not message:
            return RedirectResponse(
                f"{self.panel.prefix}/{self.slug}?error=Please+fill+in+all+forms.",
                status_code=303,
            )
        from datetime import datetime, timezone

        _quick_notes.insert(
            0,
            {
                "author": author,
                "message": message,
                "posted_at": datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC"),
            },
        )
        return RedirectResponse(
            f"{self.panel.prefix}/{self.slug}?success=Note+posted.",
            status_code=303,
        )


# ===========================================================================
# Panel
# ===========================================================================

admin_panel = AdminPanel(
    title="Kibrary Admin",
    prefix="/admin",
    per_page=10,
    auth=DatabaseAuthBackend(
        user_model=StaffUser,
        session_factory=_get_session,
        username_field="email",
        password_field="password",
        secret_key="dev-secret-key-change-in-production",
        extra_fields=["name", "role"],
    ),
    permission_checker=db_permission_checker,
    template_dirs=[_EXAMPLE_TEMPLATES],
)

register_flowbite(admin_panel)
register_components(admin_panel)
admin_panel.register_page(ReportsPage)
admin_panel.register(AuthorResource)
admin_panel.register(SubjectResource)
admin_panel.register(BookResource)
admin_panel.register(MemberResource)
admin_panel.register(CheckoutResource)
admin_panel.register(StaffUserResource)
admin_panel.register(RoleResource)
admin_panel.mount(app)


@app.get("/")
async def root():
    return {
        "app": "Kibrary — Nuru Library Demo",
        "admin": "/admin  (admin@kibrary.org / secret)",
    }
