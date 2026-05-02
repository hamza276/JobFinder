import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.services.fetcher.react_agent import ReActJobAgent, ScoredJob
from app.services.fetcher.searxng_client import SearXNGClient
from app.services.fetcher.scrapling_client import ScraplingClient
from app.services.parser.jd_extractor import JDExtractor
from app.services.llm.base import get_llm_provider
from app.services.llm.email_composer import EmailComposer

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


async def run_scan_for_user(user_id: str, db_session) -> ScanResult:
    """Full scan pipeline for one user. Entry point for Celery tasks."""
    result = ScanResult(user_id=user_id)

    try:
        from app.models.profile import UserProfile
        from app.models.scan_log import ScanLog
        from sqlalchemy import select

        user_uuid = uuid.UUID(str(user_id))

        # Load profile
        q = await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == user_uuid)
        )
        profile = q.scalar_one_or_none()
        if not profile:
            result.status = "failed"
            result.errors.append("Profile not found")
            return result

        # Initialize services
        llm = get_llm_provider()
        searxng = SearXNGClient()
        scraper = ScraplingClient()
        extractor = JDExtractor(llm=llm)
        agent = ReActJobAgent(llm=llm, searxng=searxng, scraper=scraper, extractor=extractor)

        # Run the agent
        scored_jobs: list[ScoredJob] = await agent.run(profile)
        result.jobs_found = len(scored_jobs)

        # Save to DB
        result.jobs_new = await save_jobs_to_db(scored_jobs, user_id, db_session)
        result.jobs_skipped = result.jobs_found - result.jobs_new

        # Generate emails for jobs with contact emails
        new_jobs_with_email = [j for j in scored_jobs if j.extracted.contact_email]
        if new_jobs_with_email:
            await generate_emails_for_new_jobs(
                jobs=new_jobs_with_email,
                profile=profile,
                user_id=user_id,
                db_session=db_session,
            )

        profile.last_scanned_at = datetime.utcnow()
        db_session.add(ScanLog(
            user_id=user_uuid,
            started_at=result.started_at,
            finished_at=datetime.utcnow(),
            status=result.status,
            jobs_found=result.jobs_found,
            jobs_new=result.jobs_new,
            error_message="\n".join(result.errors) if result.errors else None,
        ))
        await db_session.commit()

        await searxng.close()

    except Exception as e:
        logger.exception(f"Scan failed for user {user_id}")
        result.status = "failed"
        result.errors.append(str(e))

    result.finished_at = datetime.utcnow()
    return result


async def save_jobs_to_db(scored_jobs: list[ScoredJob], user_id: str, db_session) -> int:
    """Save jobs to DB. Returns count of genuinely new jobs (not duplicates)."""
    from app.models.job import Job
    from sqlalchemy import select

    user_uuid = uuid.UUID(str(user_id))
    new_count = 0
    for sj in scored_jobs:
        # Check for duplicate URL
        existing = await db_session.execute(
            select(Job.id).where(Job.source_url == sj.source_url)
        )
        if existing.scalar_one_or_none():
            continue

        job = Job(
            id=uuid.uuid4(),
            user_id=user_uuid,
            source_url=sj.source_url,
            source_platform=sj.source_platform,
            title=sj.extracted.title,
            company=sj.extracted.company,
            location=sj.extracted.location,
            job_type=sj.extracted.job_type,
            salary_range=sj.extracted.salary_range,
            posted_at=sj.extracted.posted_at,
            description_raw=sj.extracted.description_clean,
            description_short=sj.extracted.description_short,
            contact_email=sj.extracted.contact_email,
            relevance_score=sj.relevance_score,
            relevance_reason=sj.relevance_reason,
            fetched_at=sj.fetched_at,
        )
        db_session.add(job)
        new_count += 1

    await db_session.commit()
    logger.info(f"Saved {new_count} new jobs for user {user_id}")
    return new_count


async def generate_emails_for_new_jobs(jobs, profile, user_id: str, db_session) -> None:
    """Generate email drafts for jobs that have a contact email in JD."""
    from app.models.email_draft import EmailDraft
    from app.models.job import Job

    llm = get_llm_provider()
    composer = EmailComposer(llm=llm)

    for job_or_scored in jobs:
        try:
            # Handle both Job model and ScoredJob
            if hasattr(job_or_scored, 'extracted'):
                # ScoredJob
                contact_email = job_or_scored.extracted.contact_email
                # We need the saved Job from DB — look it up
                from sqlalchemy import select
                q = await db_session.execute(
                    select(Job).where(Job.source_url == job_or_scored.source_url)
                )
                job = q.scalar_one_or_none()
                if not job:
                    continue
            else:
                job = job_or_scored
                contact_email = job.contact_email

            email = await composer.compose(profile=profile, job=job, contact_email=contact_email)
            draft = EmailDraft(
                id=uuid.uuid4(),
                job_id=job.id,
                user_id=uuid.UUID(str(user_id)),
                to_email=email.to,
                subject=email.subject,
                body=email.body,
            )
            db_session.add(draft)

        except Exception as e:
            logger.warning(f"Email generation failed for job {getattr(job_or_scored, 'id', '?')}: {e}")

    await db_session.commit()
