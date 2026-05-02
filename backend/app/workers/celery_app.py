import asyncio
import logging
import uuid
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

logger = logging.getLogger(__name__)

app = Celery(
    "pkjobs",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.celery_app"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Karachi",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "daily-job-scan": {
            "task": "app.workers.celery_app.scan_all_users",
            "schedule": crontab(hour=1, minute=0),  # 6 AM PKT = 1 AM UTC
        }
    },
)


@app.task(name="app.workers.celery_app.scan_all_users", bind=True, max_retries=2)
def scan_all_users(self):
    """Triggered daily. Dispatches per-user scan tasks."""
    async def _run():
        from app.db.session import get_db_context
        from app.models.user import User
        from sqlalchemy import select

        async with get_db_context() as session:
            result = await session.execute(select(User.id))
            user_ids = [str(row[0]) for row in result.fetchall()]

        logger.info(f"Daily scan: dispatching tasks for {len(user_ids)} users")
        for user_id in user_ids:
            scan_user_jobs.delay(user_id)

    asyncio.run(_run())


@app.task(name="app.workers.celery_app.scan_user_jobs", bind=True, max_retries=2)
def scan_user_jobs(self, user_id: str):
    """Runs the full ReAct agent pipeline for one user."""
    async def _run():
        from app.db.session import get_db_context
        from app.services.scheduler.daily_runner import run_scan_for_user

        async with get_db_context() as session:
            result = await run_scan_for_user(user_id=user_id, db_session=session)
            logger.info(
                f"Scan complete for {user_id}: "
                f"{result.jobs_new} new / {result.jobs_found} found / {result.jobs_skipped} skipped"
            )

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.error(f"Scan failed for user {user_id}: {exc}")
        raise self.retry(exc=exc, countdown=300)  # retry after 5 min


@app.task(name="app.workers.celery_app.generate_email_for_job")
def generate_email_for_job(job_id: str, user_id: str):
    """Generate and save an email draft for a specific job."""
    async def _run():
        from app.db.session import get_db_context
        from app.services.scheduler.daily_runner import generate_emails_for_new_jobs
        from app.models.job import Job
        from app.models.profile import UserProfile
        from sqlalchemy import select

        job_uuid = uuid.UUID(str(job_id))
        user_uuid = uuid.UUID(str(user_id))
        async with get_db_context() as session:
            result = await session.execute(select(Job).where(Job.id == job_uuid))
            job = result.scalar_one_or_none()
            profile_result = await session.execute(
                select(UserProfile).where(UserProfile.user_id == user_uuid)
            )
            profile = profile_result.scalar_one_or_none()
            if job and profile:
                await generate_emails_for_new_jobs([job], profile, user_id, session)

    asyncio.run(_run())
