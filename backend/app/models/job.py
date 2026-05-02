import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.email_draft import EmailDraft
    from app.models.user import User


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_user_score_fetched", "user_id", "relevance_score", "fetched_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    source_url: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    source_platform: Mapped[str | None] = mapped_column(String(100))

    title: Mapped[str | None] = mapped_column(String(255))
    company: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    job_type: Mapped[str | None] = mapped_column(String(100))
    salary_range: Mapped[str | None] = mapped_column(String(255))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime)

    description_raw: Mapped[str] = mapped_column(Text, default="", nullable=False)
    description_short: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255))

    relevance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    relevance_reason: Mapped[str | None] = mapped_column(Text)

    is_viewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="jobs")
    email_draft: Mapped["EmailDraft | None"] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        uselist=False,
    )

    @property
    def description_clean(self) -> str:
        return self.description_raw
