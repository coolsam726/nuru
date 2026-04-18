from typing import Optional
from sqlmodel import SQLModel, Field as SMField


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

