from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Text, Uuid
from sqlmodel import Field, Relationship, SQLModel

from app.models.user import utcnow

if TYPE_CHECKING:
    from app.models.user import User


class Note(SQLModel, table=True):
    __tablename__ = "notes"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    title: str = Field(max_length=200)
    content: str = Field(default="", sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
    owner: "User" = Relationship(back_populates="notes")
