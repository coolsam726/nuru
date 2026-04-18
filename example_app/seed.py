"""example_app.seed — populate the database with initial data."""
from datetime import date

from sqlmodel import select as sm_select

from nuru import Role, Permission, RolePermission, UserRole
from example_app.db import get_session
from example_app.models import StaffUser, Author, Subject, Book, Member, Checkout


async def seed_all() -> None:
    async with get_session() as session:
        await _seed_roles(session)
        await _seed_staff_users(session)
        await _seed_authors(session)
        await _seed_subjects(session)
        await _seed_books(session)
        await _seed_members(session)
        await _seed_checkouts(session)


async def _seed_roles(session) -> None:
    if (await session.exec(sm_select(Role))).first():
        return

    super_admin = Role(name="Super Admin", description="Full access")
    librarian   = Role(name="Librarian",   description="Manage books and checkouts")
    read_only   = Role(name="Read Only",   description="View-only access")
    session.add_all([super_admin, librarian, read_only])
    await session.flush()

    star_perm = (
        await session.exec(sm_select(Permission).where(Permission.codename == "*"))
    ).first()
    if star_perm:
        session.add(RolePermission(role_id=super_admin.id, permission_id=star_perm.id))

    lib_codenames = [
        "author:list", "author:view", "author:create", "author:edit",
        "subject:list", "subject:view", "subject:create", "subject:edit",
        "book:list", "book:view", "book:create", "book:edit", "book:action",
        "member:list", "member:view", "member:create", "member:edit", "member:action",
        "checkout:list", "checkout:view", "checkout:create", "checkout:edit", "checkout:action",
    ]
    lib_perms = (
        await session.exec(sm_select(Permission).where(Permission.codename.in_(lib_codenames)))
    ).all()
    for p in lib_perms:
        session.add(RolePermission(role_id=librarian.id, permission_id=p.id))

    view_codenames = [
        "author:list", "author:view",
        "subject:list", "subject:view",
        "book:list",    "book:view",
        "member:list",  "member:view",
        "checkout:list", "checkout:view",
    ]
    view_perms = (
        await session.exec(sm_select(Permission).where(Permission.codename.in_(view_codenames)))
    ).all()
    for p in view_perms:
        session.add(RolePermission(role_id=read_only.id, permission_id=p.id))

    await session.commit()


async def _seed_staff_users(session) -> None:
    if (await session.exec(sm_select(StaffUser))).first():
        return

    admin_user  = StaffUser(name="Admin User",     email="admin@kibrary.org",  password="secret",       role="admin",     active=True)
    lib_user    = StaffUser(name="Jane Librarian", email="jane@kibrary.org",   password="librarian123", role="librarian", active=True)
    viewer_user = StaffUser(name="Viewer User",    email="viewer@kibrary.org", password="viewer123",    role="viewer",    active=True)
    session.add_all([admin_user, lib_user, viewer_user])
    await session.flush()

    super_admin = (await session.exec(sm_select(Role).where(Role.name == "Super Admin"))).first()
    librarian   = (await session.exec(sm_select(Role).where(Role.name == "Librarian"))).first()
    read_only   = (await session.exec(sm_select(Role).where(Role.name == "Read Only"))).first()
    if super_admin:
        session.add(UserRole(user_id=str(admin_user.id),  role_id=super_admin.id))
    if librarian:
        session.add(UserRole(user_id=str(lib_user.id),    role_id=librarian.id))
    if read_only:
        session.add(UserRole(user_id=str(viewer_user.id), role_id=read_only.id))
    await session.commit()


async def _seed_authors(session) -> None:
    if (await session.exec(sm_select(Author))).first():
        return
    session.add_all([
        Author(name="Chinua Achebe",          email="c.achebe@example.com",   nationality="Nigerian",  birth_date=date(1930, 11, 16), bio="Renowned Nigerian novelist and poet.",          active=True),
        Author(name="Ngugi wa Thiongo",        email="ngugi@example.com",      nationality="Kenyan",    birth_date=date(1938,  1,  5), bio="Leading voice of African literature.",          active=True),
        Author(name="Wole Soyinka",            email="soyinka@example.com",    nationality="Nigerian",  birth_date=date(1934,  7, 13), bio="Nobel laureate — literary and dramatic work.",  active=True),
        Author(name="Chimamanda Adichie",      email="adichie@example.com",    nationality="Nigerian",  birth_date=date(1977,  9, 15), bio="Author of Half of a Yellow Sun.",               active=True),
        Author(name="Binyavanga Wainaina",     email="binyavanga@example.com", nationality="Kenyan",    birth_date=date(1971,  1, 18), bio="Journalist and memoirist.",                     active=False),
        Author(name="Ama Ata Aidoo",           email="aidoo@example.com",      nationality="Ghanaian",  birth_date=date(1942,  3, 23), bio="Pioneer of African feminist literature.",        active=True),
        Author(name="George Orwell",                                            nationality="British",   birth_date=date(1903,  6, 25), bio="Author of 1984 and Animal Farm.",               active=True),
        Author(name="Gabriel Garcia Marquez",                                   nationality="Colombian", birth_date=date(1927,  3,  6), bio="Nobel laureate — magical realism.",             active=True),
    ])
    await session.commit()


async def _seed_subjects(session) -> None:
    if (await session.exec(sm_select(Subject))).first():
        return
    session.add_all([
        Subject(name="African Literature", code="AFL", description="Fiction and non-fiction from African writers.", floor="1st", active=True),
        Subject(name="Science Fiction",    code="SCI", description="Speculative and science fiction.",             floor="2nd", active=True),
        Subject(name="History",            code="HIS", description="World and regional history.",                  floor="2nd", active=True),
        Subject(name="Philosophy",         code="PHI", description="Classics and contemporary philosophy.",        floor="3rd", active=True),
        Subject(name="Children",           code="CHI", description="Picture books, early readers, middle grade.",  floor="G",   active=True),
        Subject(name="Reference",          code="REF", description="Encyclopaedias, dictionaries, atlases.",       floor="G",   active=True),
        Subject(name="Self Help",          code="SLF", description="Personal development and wellness.",           floor="1st", active=True),
        Subject(name="Periodicals",        code="PER", description="Journals, magazines, and newspapers.",         floor="G",   active=False),
    ])
    await session.commit()


async def _seed_books(session) -> None:
    if (await session.exec(sm_select(Book))).first():
        return
    authors  = {a.name: a.id for a in (await session.exec(sm_select(Author))).all()}
    subjects = {s.code: s.id for s in (await session.exec(sm_select(Subject))).all()}
    session.add_all([
        Book(isbn="978-0435905255", title="Things Fall Apart",             author_id=authors.get("Chinua Achebe"),          subject_id=subjects.get("AFL"), year=1958, edition="1st",       copies=4, available=True,  location="AFL-A1", notes="Classic post-colonial novel."),
        Book(isbn="978-0435905897", title="No Longer at Ease",             author_id=authors.get("Chinua Achebe"),          subject_id=subjects.get("AFL"), year=1960, edition="1st",       copies=2, available=True,  location="AFL-A1"),
        Book(isbn="978-0143039020", title="A Grain of Wheat",              author_id=authors.get("Ngugi wa Thiongo"),       subject_id=subjects.get("AFL"), year=1967, edition="2nd",       copies=3, available=True,  location="AFL-N1"),
        Book(isbn="978-0143039044", title="Petals of Blood",               author_id=authors.get("Ngugi wa Thiongo"),       subject_id=subjects.get("AFL"), year=1977, edition="1st",       copies=2, available=False, location="AFL-N1", notes="Currently under repair."),
        Book(isbn="978-0062301697", title="Half of a Yellow Sun",          author_id=authors.get("Chimamanda Adichie"),     subject_id=subjects.get("AFL"), year=2006, edition="1st",       copies=5, available=True,  location="AFL-C1"),
        Book(isbn="978-0307455925", title="Americanah",                    author_id=authors.get("Chimamanda Adichie"),     subject_id=subjects.get("AFL"), year=2013, edition="1st",       copies=3, available=True,  location="AFL-C1"),
        Book(isbn="978-0451524935", title="1984",                          author_id=authors.get("George Orwell"),          subject_id=subjects.get("SCI"), year=1949, edition="Signet",    copies=6, available=True,  location="SCI-O1", notes="Perennial bestseller."),
        Book(isbn="978-0060964344", title="One Hundred Years of Solitude", author_id=authors.get("Gabriel Garcia Marquez"), subject_id=subjects.get("AFL"), year=1967, edition="1st Eng",  copies=3, available=True,  location="AFL-G1"),
        Book(isbn="978-0140441185", title="The Analects",                                                                   subject_id=subjects.get("PHI"), year=479,  edition="Penguin",  copies=2, available=True,  location="PHI-P1"),
        Book(isbn="978-0143105954", title="Weep Not Child",                author_id=authors.get("Ngugi wa Thiongo"),       subject_id=subjects.get("AFL"), year=1964, edition="1st",       copies=2, available=True,  location="AFL-N2"),
        Book(isbn="978-0521898423", title="Death and the Kings Horseman",  author_id=authors.get("Wole Soyinka"),           subject_id=subjects.get("AFL"), year=1975, edition="Cambridge", copies=2, available=True,  location="AFL-S1"),
        Book(isbn="978-0141182803", title="Animal Farm",                   author_id=authors.get("George Orwell"),          subject_id=subjects.get("SCI"), year=1945, edition="Penguin",  copies=5, available=True,  location="SCI-O2"),
        *[
            Book(isbn=f"978-000000{100 + i:04d}", title=f"Library Acquisition {i}",
                 subject_id=subjects.get("REF"), year=2020 + (i % 5),
                 copies=1, available=i % 3 != 0, location=f"REF-{i:03d}")
            for i in range(1, 21)
        ],
    ])
    await session.commit()


async def _seed_members(session) -> None:
    if (await session.exec(sm_select(Member))).first():
        return
    session.add_all([
        Member(name="Amina Hassan",    email="amina@email.com",   phone="+254701000001", member_number="MBR-001", membership="standard", joined_on=date(2022,  1, 15), active=True),
        Member(name="Baraka Ochieng",  email="baraka@email.com",  phone="+254701000002", member_number="MBR-002", membership="student",  joined_on=date(2022,  3, 10), active=True),
        Member(name="Cynthia Waweru",  email="cynthia@email.com", phone="+254701000003", member_number="MBR-003", membership="senior",   joined_on=date(2021,  6, 20), active=True),
        Member(name="Danstan Mwenda",  email="danstan@email.com", phone="+254701000004", member_number="MBR-004", membership="standard", joined_on=date(2023,  2,  5), active=True),
        Member(name="Edith Ajuma",     email="edith@email.com",   phone="+254701000005", member_number="MBR-005", membership="staff",    joined_on=date(2020,  9,  1), active=True),
        Member(name="Francis Njoroge", email="francis@email.com", phone="+254701000006", member_number="MBR-006", membership="student",  joined_on=date(2023,  8, 22), active=True),
        Member(name="Grace Mutua",     email="grace@email.com",   phone="+254701000007", member_number="MBR-007", membership="standard", joined_on=date(2022, 11, 30), active=False, notes="Account suspended — pending renewal."),
        Member(name="Hassan Abdi",     email="hassan@email.com",  phone="+254701000008", member_number="MBR-008", membership="senior",   joined_on=date(2019,  4, 17), active=True),
        Member(name="Irene Chebet",    email="irene@email.com",   phone="+254701000009", member_number="MBR-009", membership="student",  joined_on=date(2024,  1,  8), active=True),
        Member(name="James Kipchoge",  email="james@email.com",   phone="+254701000010", member_number="MBR-010", membership="standard", joined_on=date(2021,  7, 14), active=True),
        *[
            Member(name=f"Member {i}", email=f"member{i}@email.com",
                   member_number=f"MBR-{100 + i:03d}", membership="standard",
                   joined_on=date(2023, 1, 1), active=True)
            for i in range(1, 21)
        ],
    ])
    await session.commit()


async def _seed_checkouts(session) -> None:
    if (await session.exec(sm_select(Checkout))).first():
        return
    books   = {b.title: b.id for b in (await session.exec(sm_select(Book))).all()}
    members = {m.name:  m.id for m in (await session.exec(sm_select(Member))).all()}
    session.add_all([
        Checkout(book_id=books.get("Things Fall Apart"),             member_id=members.get("Amina Hassan"),    issued_on=date(2025, 1,  5), due_date=date(2025, 1, 19), returned_on=date(2025, 1, 18), status="returned", fine_amount=0.0,   fine_paid=False),
        Checkout(book_id=books.get("1984"),                          member_id=members.get("Baraka Ochieng"),  issued_on=date(2025, 2, 10), due_date=date(2025, 2, 24),                                 status="issued",   fine_amount=0.0,   fine_paid=False, notes="Member requested extension."),
        Checkout(book_id=books.get("Half of a Yellow Sun"),          member_id=members.get("Cynthia Waweru"), issued_on=date(2024,12,  1), due_date=date(2024,12, 15),                                 status="overdue",  fine_amount=150.0, fine_paid=False, notes="Reminder SMS sent."),
        Checkout(book_id=books.get("Americanah"),                    member_id=members.get("Danstan Mwenda"), issued_on=date(2025, 3,  1), due_date=date(2025, 3, 15), returned_on=date(2025, 3, 14), status="returned", fine_amount=0.0,   fine_paid=False),
        Checkout(book_id=books.get("A Grain of Wheat"),              member_id=members.get("Edith Ajuma"),    issued_on=date(2025, 3, 20), due_date=date(2025, 4,  3),                                 status="issued",   fine_amount=0.0,   fine_paid=False),
        Checkout(book_id=books.get("Animal Farm"),                   member_id=members.get("Francis Njoroge"),issued_on=date(2025, 1, 20), due_date=date(2025, 2,  3),                                 status="overdue",  fine_amount=300.0, fine_paid=True,  notes="Fine paid at counter."),
        Checkout(book_id=books.get("One Hundred Years of Solitude"), member_id=members.get("Hassan Abdi"),    issued_on=date(2025, 3,  5), due_date=date(2025, 3, 19), returned_on=date(2025, 3, 19), status="returned", fine_amount=0.0,   fine_paid=False),
        Checkout(book_id=books.get("Death and the Kings Horseman"),  member_id=members.get("Irene Chebet"),   issued_on=date(2025, 4,  1), due_date=date(2025, 4, 15),                                 status="issued",   fine_amount=0.0,   fine_paid=False),
        Checkout(book_id=books.get("No Longer at Ease"),             member_id=members.get("James Kipchoge"), issued_on=date(2025, 2,  1), due_date=date(2025, 2, 15),                                 status="lost",     fine_amount=500.0, fine_paid=False, notes="Member reported book lost."),
        Checkout(book_id=books.get("1984"),                          member_id=members.get("Amina Hassan"),   issued_on=date(2025, 4,  5), due_date=date(2025, 4, 19),                                 status="issued",   fine_amount=0.0,   fine_paid=False),
    ])
    await session.commit()

