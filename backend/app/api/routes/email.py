import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.email_draft import EmailDraft
from app.models.job import Job
from app.models.profile import UserProfile
from app.services.llm.base import get_llm_provider
from app.services.llm.email_composer import EmailComposer

router = APIRouter()


class EmailDraftResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    user_id: uuid.UUID
    to_email: str | None
    subject: str
    body: str
    is_regenerated: bool
    created_at: Any

    model_config = ConfigDict(from_attributes=True)


@router.get("/{job_id}", response_model=EmailDraftResponse)
async def get_email(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> EmailDraft:
    existing = await _get_draft(db, job_id)
    if existing:
        return existing

    job, profile = await _get_job_and_profile(db, job_id)
    draft = await _compose_and_save(db, job, profile, is_regenerated=False)
    return draft


@router.post("/{job_id}/regenerate", response_model=EmailDraftResponse)
async def regenerate_email(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> EmailDraft:
    job, profile = await _get_job_and_profile(db, job_id)
    existing = await _get_draft(db, job_id)

    composer = EmailComposer(llm=get_llm_provider())
    composed = await composer.compose(profile=profile, job=job, contact_email=job.contact_email)

    if existing:
        existing.to_email = composed.to
        existing.subject = composed.subject
        existing.body = composed.body
        existing.is_regenerated = True
        existing.created_at = datetime.utcnow()
        await db.commit()
        await db.refresh(existing)
        return existing

    return await _compose_and_save(db, job, profile, is_regenerated=True)


async def _get_draft(db: AsyncSession, job_id: uuid.UUID) -> EmailDraft | None:
    result = await db.execute(select(EmailDraft).where(EmailDraft.job_id == job_id))
    return result.scalar_one_or_none()


async def _get_job_and_profile(db: AsyncSession, job_id: uuid.UUID) -> tuple[Job, UserProfile]:
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == job.user_id))
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return job, profile


async def _compose_and_save(
    db: AsyncSession,
    job: Job,
    profile: UserProfile,
    is_regenerated: bool,
) -> EmailDraft:
    composer = EmailComposer(llm=get_llm_provider())
    composed = await composer.compose(profile=profile, job=job, contact_email=job.contact_email)
    draft = EmailDraft(
        job_id=job.id,
        user_id=job.user_id,
        to_email=composed.to,
        subject=composed.subject,
        body=composed.body,
        is_regenerated=is_regenerated,
    )
    db.add(draft)
    await db.commit()
    await db.refresh(draft)
    return draft
