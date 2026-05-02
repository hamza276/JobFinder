# Workers — Celery Configuration

## Purpose
Manages async task execution and scheduled jobs via Celery + Redis.

## `celery_app.py`
Creates and configures the Celery application.

```python
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

app = Celery(
    "pkjobs",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"]
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    timezone="Asia/Karachi",
    beat_schedule={
        "daily-job-scan": {
            "task": "app.workers.tasks.scan_all_users",
            "schedule": crontab(hour=1, minute=0),  # 6 AM PKT
        }
    }
)
```

## Tasks (in `tasks.py`)

### `scan_all_users`
- Beat-triggered task
- Gets all user IDs from DB
- Calls `scan_user_jobs.delay(user_id)` for each

### `scan_user_jobs(user_id: str)`
- Main worker task
- Creates async DB session
- Calls `run_scan_for_user(user_id, session)` from scheduler service
- Handles exceptions, logs to scan_logs table

### `generate_email_for_job(job_id: str, user_id: str)`
- Called after new job saved if contact_email found
- Generates and saves EmailDraft
- Can also be triggered manually from `/api/email/{job_id}/regenerate`

## Running Workers
```bash
# Worker process (handles task execution)
celery -A app.workers.celery_app worker --loglevel=info --concurrency=4

# Beat process (handles scheduling — run only ONE instance)
celery -A app.workers.celery_app beat --loglevel=info

# Monitor tasks (optional, great for dev)
celery -A app.workers.celery_app flower --port=5555
```

## Important Notes
- Celery tasks CANNOT use `async def` directly — use `asyncio.run()` inside sync task to call async code
- Or use `celery-pool-asyncio` package for native async support
- Never import FastAPI `app` inside Celery tasks — only import services/models
- Use `task_acks_late=True` to ensure tasks aren't lost if worker crashes mid-execution
