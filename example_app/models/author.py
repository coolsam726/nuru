from typing import Optional, TYPE_CHECKING
from datetime import date
from sqlmodel import SQLModel, Field as SMField, Relationship

if TYPE_CHECKING:
    from .book import Book


class Author(SQLModel, table=True):
    __tablename__ = "authors"
    id: Optional[int] = SMField(default=None, primary_key=True)
    name: str
    email: Optional[str] = None
    nationality: Optional[str] = None
    birth_date: Optional[date] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None
    active: bool = True
    books: list["Book"] = Relationship(back_populates="author")

    def __str__(self) -> str:
        return self.name

