from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field as SMField, Relationship
from .author import Author
from .subject import Subject


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
    subject: Optional[Subject] = Relationship()

    def __str__(self) -> str:
        return self.title

