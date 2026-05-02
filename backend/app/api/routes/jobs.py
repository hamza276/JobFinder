import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.models.email_draft import EmailDraft
from app.models.job import Job
from app.models.profile import UserProfile

router = APIRouter()


class JobResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    source_url: str
    source_platform: str | None
    title: str | None
    company: str | None
    location: str | None
    job_type: str | None
    salary_range: str | None
    posted_at: Any = None
    description_raw: str
    description_short: str
    contact_email: str | None
    relevance_score: float
    relevance_reason: str | None
    is_viewed: bool
    is_hidden: bool
    fetched_at: Any
    created_at: Any

    model_config = ConfigDict(from_attributes=True)


class JobsPageResponse(BaseModel):
    jobs: list[JobResponse]
    page: int
    limit: int
    total: int
    has_more: bool


class TriggerScanRequest(BaseModel):
    user_id: uuid.UUID


class TriggerScanResponse(BaseModel):
    accepted: bool
    user_id: uuid.UUID
    message: str


class MarkViewedRequest(BaseModel):
    is_hidden: bool = False


class JobStatsResponse(BaseModel):
    user_id: uuid.UUID
    total_found: int
    viewed: int
    hidden: int
    emails_generated: int
    high_matches: int
    last_scan_at: Any = None


@router.post("/trigger", response_model=TriggerScanResponse)
async def trigger_scan(
    payload: TriggerScanRequest,
    db: AsyncSession = Depends(get_db),
) -> TriggerScanResponse:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == payload.user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    cooldown_remaining = await _cooldown_remaining(str(payload.user_id))
    if cooldown_remaining > 0:
        return TriggerScanResponse(
            accepted=False,
            user_id=payload.user_id,
            message=f"Scan already requested. Try again in {cooldown_remaining} seconds.",
        )

    profile.manual_scan_requested_at = datetime.utcnow()
    await db.commit()
    await _set_cooldown(str(payload.user_id))

    try:
        from app.workers.celery_app import scan_user_jobs

        scan_user_jobs.delay(str(payload.user_id))
        return TriggerScanResponse(
            accepted=True,
            user_id=payload.user_id,
            message="Scan queued.",
        )
    except Exception as exc:
        return TriggerScanResponse(
            accepted=False,
            user_id=payload.user_id,
            message=f"Could not queue scan: {exc}",
        )


@router.get("/{user_id}/stats", response_model=JobStatsResponse)
async def get_job_stats(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> JobStatsResponse:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    total = await _count(db, select(func.count(Job.id)).where(Job.user_id == user_id))
    viewed = await _count(db, select(func.count(Job.id)).where(Job.user_id == user_id, Job.is_viewed.is_(True)))
    hidden = await _count(db, select(func.count(Job.id)).where(Job.user_id == user_id, Job.is_hidden.is_(True)))
    high = await _count(db, select(func.count(Job.id)).where(Job.user_id == user_id, Job.relevance_score >= 0.7))
    emails = await _count(db, select(func.count(EmailDraft.id)).where(EmailDraft.user_id == user_id))

    return JobStatsResponse(
        user_id=user_id,
        total_found=total,
        viewed=viewed,
        hidden=hidden,
        emails_generated=emails,
        high_matches=high,
        last_scan_at=profile.last_scanned_at,
    )


@router.get("/{user_id}", response_model=JobsPageResponse)
async def get_jobs(
    user_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    include_viewed: bool = False,
    db: AsyncSession = Depends(get_db),
) -> JobsPageResponse:
    profile_result = await db.execute(select(UserProfile.id).where(UserProfile.user_id == user_id))
    if not profile_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Profile not found")

    filters = [Job.user_id == user_id, Job.is_hidden.is_(False)]
    if not include_viewed:
        filters.append(Job.is_viewed.is_(False))

    total = await _count(db, select(func.count(Job.id)).where(*filters))
    offset = (page - 1) * limit
    result = await db.execute(
        select(Job)
        .where(*filters)
        .order_by(desc(Job.relevance_score), desc(Job.fetched_at))
        .offset(offset)
        .limit(limit)
    )
    jobs = list(result.scalars().all())
    return JobsPageResponse(
        jobs=jobs,
        page=page,
        limit=limit,
        total=total,
        has_more=offset + len(jobs) < total,
    )


@router.patch("/{job_id}/viewed", response_model=JobResponse)
async def mark_job_viewed(
    job_id: uuid.UUID,
    payload: MarkViewedRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.is_viewed = True
    if payload and payload.is_hidden:
        job.is_hidden = True
    await db.commit()
    await db.refresh(job)
    return job


async def _count(db: AsyncSession, statement) -> int:
    result = await db.execute(statement)
    return int(result.scalar_one() or 0)


async def _cooldown_remaining(user_id: str) -> int:
    try:
        from redis.asyncio import Redis

        redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        ttl = await redis.ttl(f"manual_scan:{user_id}")
        await redis.aclose()
        return max(ttl, 0)
    except Exception:
        return 0


async def _set_cooldown(user_id: str) -> None:
    try:
        from redis.asyncio import Redis

        redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis.setex(
            f"manual_scan:{user_id}",
            settings.MANUAL_SCAN_COOLDOWN_SECONDS,
            "1",
        )
        await redis.aclose()
    except Exception:
        return None
