from typing import Optional
from sqlmodel import SQLModel, Field as SMField


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

