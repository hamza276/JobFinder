import logging
import uuid
import asyncio
from dataclasses import dataclass, field
from datetime import datetime

from app.core.config import settings
from app.services.fetcher.react_agent import ReActJobAgent, ScoredJob
from app.services.fetcher.scrapling_client import ScraplingClient
from app.services.fetcher.searxng_client import SearXNGClient
from app.services.llm.base import get_llm_provider
from app.services.llm.email_composer import EmailComposer
from app.services.parser.jd_extractor import JDExtractor

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    user_id: str
    jobs_found: int = 0
    jobs_new: int = 0
    jobs_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None
    status: str = "success"


@dataclass
class JobSaveResult:
    saved_jobs: list
    skipped_count: int = 0

    @property
    def new_count(self) -> int:
        return len(self.saved_jobs)


async def run_scan_for_user(user_id: str, db_session) -> ScanResult:
    """Run the full scan pipeline for one user."""
    from app.models.profile import UserProfile
    from sqlalchemy import select

    result = ScanResult(user_id=user_id)
    user_uuid = uuid.UUID(str(user_id))
    profile = None
    searxng = None

    try:
        profile_result = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == user_uuid)
        )
        profile = profile_result.scalar_one_or_none()
        if not profile:
            result.status = "failed"
            result.errors.append("Profile not found")
            return result

        llm = get_llm_provider()
        searxng = SearXNGClient()
        scraper = ScraplingClient()
        extractor = JDExtractor(llm=llm)
        agent = ReActJobAgent(llm=llm, searxng=searxng, scraper=scraper, extractor=extractor)

        try:
            scored_jobs: list[ScoredJob] = await asyncio.wait_for(
                agent.run(profile),
                timeout=settings.REACT_AGENT_SCAN_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            result.status = "partial"
            result.errors.append(
                f"Scan timed out after {settings.REACT_AGENT_SCAN_TIMEOUT_SECONDS} seconds"
            )
            scored_jobs = []
        result.jobs_found = len(scored_jobs)

        save_result = await save_jobs_to_db(scored_jobs, user_id, db_session)
        result.jobs_new = save_result.new_count
        result.jobs_skipped = result.jobs_found - result.jobs_new

        jobs_with_email = [job for job in save_result.saved_jobs if job.contact_email]
        if jobs_with_email:
            await generate_emails_for_new_jobs(
                jobs=jobs_with_email,
                profile=profile,
                user_id=user_id,
                db_session=db_session,
            )

        profile.last_scanned_at = datetime.utcnow()

    except Exception as exc:
        await _rollback_quietly(db_session)
        logger.exception("Scan failed for user %s", user_id)
        result.status = "failed"
        result.errors.append(str(exc))

    finally:
        result.finished_at = datetime.utcnow()
        if searxng is not None:
            try:
                await searxng.close()
            except Exception:
                logger.debug("Failed to close SearXNG client", exc_info=True)

        if profile is not None:
            await _record_scan_log(db_session, user_uuid, result)

    return result


async def save_jobs_to_db(scored_jobs: list[ScoredJob], user_id: str, db_session) -> JobSaveResult:
    """Persist new jobs and skip URLs already present in the database."""
    from app.models.job import Job
    from sqlalchemy import select

    user_uuid = uuid.UUID(str(user_id))
    saved_jobs = []
    skipped_count = 0

    for scored_job in scored_jobs:
        existing = await db_session.execute(
            select(Job.id).where(Job.source_url == scored_job.source_url)
        )
        if existing.scalar_one_or_none():
            skipped_count += 1
            continue

        job = Job(
            id=uuid.uuid4(),
            user_id=user_uuid,
            source_url=scored_job.source_url,
            source_platform=scored_job.source_platform,
            title=scored_job.extracted.title,
            company=scored_job.extracted.company,
            location=scored_job.extracted.location,
            job_type=scored_job.extracted.job_type,
            salary_range=scored_job.extracted.salary_range,
            posted_at=scored_job.extracted.posted_at,
            description_raw=scored_job.extracted.description_clean,
            description_short=scored_job.extracted.description_short,
            contact_email=scored_job.extracted.contact_email,
            relevance_score=scored_job.relevance_score,
            relevance_reason=scored_job.relevance_reason,
            fetched_at=scored_job.fetched_at,
        )
        db_session.add(job)
        saved_jobs.append(job)

    await db_session.commit()
    logger.info("Saved %s new jobs for user %s", len(saved_jobs), user_id)
    return JobSaveResult(saved_jobs=saved_jobs, skipped_count=skipped_count)


async def generate_emails_for_new_jobs(jobs, profile, user_id: str, db_session) -> None:
    """Generate idempotent email drafts for jobs that do not already have one."""
    from app.models.email_draft import EmailDraft
    from app.models.job import Job
    from sqlalchemy import select

    llm = get_llm_provider()
    composer = EmailComposer(llm=llm)
    user_uuid = uuid.UUID(str(user_id))

    for job_or_scored in jobs:
        try:
            if hasattr(job_or_scored, "extracted"):
                contact_email = job_or_scored.extracted.contact_email
                job_result = await db_session.execute(
                    select(Job).where(Job.source_url == job_or_scored.source_url)
                )
                job = job_result.scalar_one_or_none()
                if not job:
                    continue
            else:
                job = job_or_scored
                contact_email = job.contact_email

            existing = await db_session.execute(
                select(EmailDraft.id).where(EmailDraft.job_id == job.id)
            )
            if existing.scalar_one_or_none():
                continue

            email = await composer.compose(profile=profile, job=job, contact_email=contact_email)
            db_session.add(
                EmailDraft(
                    id=uuid.uuid4(),
                    job_id=job.id,
                    user_id=user_uuid,
                    to_email=email.to,
                    subject=email.subject,
                    body=email.body,
                )
            )

        except Exception as exc:
            logger.warning(
                "Email generation failed for job %s: %s",
                getattr(job_or_scored, "id", "?"),
                exc,
            )

    await db_session.commit()


async def _record_scan_log(db_session, user_id: uuid.UUID, result: ScanResult) -> None:
    from app.models.scan_log import ScanLog

    try:
        db_session.add(
            ScanLog(
                user_id=user_id,
                started_at=result.started_at,
                finished_at=result.finished_at,
                status=result.status,
                jobs_found=result.jobs_found,
                jobs_new=result.jobs_new,
                error_message="\n".join(result.errors) if result.errors else None,
            )
        )
        await db_session.commit()
    except Exception:
        await _rollback_quietly(db_session)
        logger.exception("Failed to record scan log for user %s", user_id)


async def _rollback_quietly(db_session) -> None:
    try:
        await db_session.rollback()
    except Exception:
        logger.debug("Session rollback failed", exc_info=True)
