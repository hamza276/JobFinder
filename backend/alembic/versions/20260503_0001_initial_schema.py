"""Initial schema

Revision ID: 20260503_0001
Revises:
Create Date: 2026-05-03 00:25:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260503_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_url", sa.String(length=1024), nullable=False),
        sa.Column("source_platform", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("job_type", sa.String(length=100), nullable=True),
        sa.Column("salary_range", sa.String(length=255), nullable=True),
        sa.Column("posted_at", sa.DateTime(), nullable=True),
        sa.Column("description_raw", sa.Text(), nullable=False),
        sa.Column("description_short", sa.String(length=500), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column("relevance_reason", sa.Text(), nullable=True),
        sa.Column("is_viewed", sa.Boolean(), nullable=False),
        sa.Column("is_hidden", sa.Boolean(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_jobs_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
        sa.UniqueConstraint("source_url", name=op.f("uq_jobs_source_url")),
    )
    op.create_index(op.f("ix_jobs_user_id"), "jobs", ["user_id"], unique=False)
    op.create_index("ix_jobs_user_score_fetched", "jobs", ["user_id", "relevance_score", "fetched_at"], unique=False)
    op.create_table(
        "scan_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("jobs_found", sa.Integer(), nullable=False),
        sa.Column("jobs_new", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_scan_logs_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scan_logs")),
    )
    op.create_index(op.f("ix_scan_logs_user_id"), "scan_logs", ["user_id"], unique=False)
    op.create_table(
        "user_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("current_title", sa.String(length=255), nullable=False),
        sa.Column("experience_years", sa.Integer(), nullable=False),
        sa.Column("skills", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("education", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("preferred_locations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("preferred_job_types", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("industries", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("languages", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("last_scanned_at", sa.DateTime(), nullable=True),
        sa.Column("manual_scan_requested_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_user_profiles_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_profiles")),
    )
    op.create_index(op.f("ix_user_profiles_user_id"), "user_profiles", ["user_id"], unique=True)
    op.create_table(
        "email_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_email", sa.String(length=255), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_regenerated", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], name=op.f("fk_email_drafts_job_id_jobs"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_email_drafts_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_drafts")),
    )
    op.create_index(op.f("ix_email_drafts_job_id"), "email_drafts", ["job_id"], unique=True)
    op.create_index(op.f("ix_email_drafts_user_id"), "email_drafts", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_email_drafts_user_id"), table_name="email_drafts")
    op.drop_index(op.f("ix_email_drafts_job_id"), table_name="email_drafts")
    op.drop_table("email_drafts")
    op.drop_index(op.f("ix_user_profiles_user_id"), table_name="user_profiles")
    op.drop_table("user_profiles")
    op.drop_index(op.f("ix_scan_logs_user_id"), table_name="scan_logs")
    op.drop_table("scan_logs")
    op.drop_index("ix_jobs_user_score_fetched", table_name="jobs")
    op.drop_index(op.f("ix_jobs_user_id"), table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("users")
