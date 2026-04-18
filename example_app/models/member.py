from typing import Optional, TYPE_CHECKING
from datetime import date
from sqlmodel import SQLModel, Field as SMField, Relationship

if TYPE_CHECKING:
    from .checkout import Checkout


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
    avatar: Optional[str] = None
    checkouts: list["Checkout"] = Relationship(back_populates="member")

    def __str__(self) -> str:
        return f"{self.name} ({self.member_number})"

