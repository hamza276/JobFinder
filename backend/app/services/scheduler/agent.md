# Scheduler Service — Daily Job Fetching

## Purpose
Runs the ReAct agent pipeline daily for every user in the system.

## How It Works
1. **Celery Beat** triggers `scan_all_users` task every day at **6:00 AM PKT** (01:00 UTC)
2. `scan_all_users` fetches all active user IDs from DB
3. For each user, it dispatches a separate `scan_user_jobs` task to the Celery queue
4. Each `scan_user_jobs` task:
   - Loads the user's `UserProfile` from DB
   - Instantiates `ReActJobAgent`
   - Calls `agent.run(profile)` → returns list of `ScoredJob`
   - Saves new jobs to DB (skips duplicates by URL)
   - Generates `EmailDraft` for jobs where `contact_email` is found
   - Updates `last_scanned_at` on the user's profile

## Schedule Configuration (in `celery_app.py`)
```python
app.conf.beat_schedule = {
    "daily-job-scan": {
        "task": "app.workers.tasks.scan_all_users",
        "schedule": crontab(hour=1, minute=0),   # 6 AM PKT = 1 AM UTC
    }
}
```

## Manual Trigger
Users can click "Scan Now" in the dashboard.
This calls `POST /api/jobs/trigger` → which directly calls `scan_user_jobs.delay(user_id)`.
Rate limited: max 1 manual trigger per user per hour (stored in Redis).

## `daily_runner.py` Functions
```python
async def run_scan_for_user(user_id: str, db_session) -> ScanResult:
    """
    Full scan pipeline for one user.
    Returns ScanResult with: jobs_found, jobs_new, jobs_skipped, errors
    """

async def save_jobs_to_db(jobs: List[ScoredJob], user_id: str, db_session) -> int:
    """
    Upsert jobs. Returns count of NEW jobs added (not duplicates).
    """

async def generate_emails_for_new_jobs(jobs: List[Job], user_id: str, db_session):
    """
    For jobs with contact_email, generate and save EmailDraft.
    Runs after save_jobs_to_db.
    """
```

## Error Handling
- If ReAct agent fails for a user: log error, continue to next user (don't fail all)
- If Scrapling cannot fetch a protected page: log the URL, continue with the next candidate, and mark scan as "partial" if needed
- All scan results logged to DB table `scan_logs` for debugging

## Scan Log Model (add to models/)
```
scan_logs table:
  id              UUID
  user_id         UUID FK
  started_at      TIMESTAMP
  finished_at     TIMESTAMP
  status          VARCHAR   ← "success" | "partial" | "failed"
  jobs_found      INTEGER
  jobs_new        INTEGER
  error_message   TEXT
```
