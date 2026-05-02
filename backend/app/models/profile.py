import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    current_title: Mapped[str] = mapped_column(String(255), nullable=False)
    experience_years: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skills: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    education: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    preferred_locations: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    preferred_job_types: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    industries: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    languages: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    bio: Mapped[str | None] = mapped_column(Text)
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime)
    manual_scan_requested_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="profile")
