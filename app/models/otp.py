from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, String
from sqlmodel import Field, SQLModel

from app.models.user import utcnow


class OTPPurpose(str, Enum):
    REGISTER = "register"
    RESET_PASSWORD = "reset_password"


class OTP(SQLModel, table=True):
    __tablename__ = "otps"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    code: str = Field(sa_column=Column(String(6), nullable=False))
    purpose: str = Field(sa_column=Column(String(30), index=True, nullable=False))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    is_used: bool = False
    attempts: int = 0
    created_at: datetime = Field(default_factory=utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
