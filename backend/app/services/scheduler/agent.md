# Scheduler Service - Scan Orchestration

## Purpose
Runs job discovery for users through Celery tasks and direct service calls.

## Daily Flow
1. Celery Beat triggers `scan_all_users` at 6:00 AM PKT.
2. `scan_all_users` dispatches `scan_user_jobs` for each user.
3. `scan_user_jobs` calls `run_scan_for_user(user_id, db_session)`.
4. The scan loads the profile, runs `ReActJobAgent`, saves new jobs, generates email drafts where contact emails exist, updates `last_scanned_at`, and writes a `ScanLog`.

## `daily_runner.py`
- `run_scan_for_user`: full orchestration and scan logging.
- `save_jobs_to_db`: persists new jobs and skips duplicate source URLs.
- `generate_emails_for_new_jobs`: idempotently creates one `EmailDraft` per job.

## Current Guarantees
- Scan failures are captured in `ScanResult.errors`.
- Agent scans are wrapped in `REACT_AGENT_SCAN_TIMEOUT_SECONDS`; timeout scans are marked `partial`.
- DB rollback is attempted on scan failure.
- `ScanLog` is written in the `finally` path when a profile was loaded.
- Email draft generation skips jobs that already have a draft.
- Only saved jobs with `contact_email` are passed to automatic email generation.

## Manual Trigger
`POST /api/jobs/trigger` queues `scan_user_jobs.delay(user_id)` and is rate-limited through Redis by `MANUAL_SCAN_COOLDOWN_SECONDS`.

## Notes For Future Changes
- Keep Celery tasks thin; orchestration belongs here.
- If scan result fields or persistence semantics change, update this file and `backend/tests/test_scheduler_services.py`.
