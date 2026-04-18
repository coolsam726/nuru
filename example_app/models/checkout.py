from typing import Optional
from datetime import date
from sqlmodel import SQLModel, Field as SMField, Relationship
from .book import Book
from .member import Member


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
    attachment: Optional[str] = None

    def __str__(self) -> str:
        return f"Checkout #{self.id}"

