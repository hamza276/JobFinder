# Docs

## Contents
- `flow.md` — Complete user journey and system data flow. Read this first if you're new to the project.

## Key Design Decisions (with reasoning)

### Why ReAct Agent instead of simple scheduled scraper?
A fixed scraper with hardcoded queries quickly becomes stale. The ReAct agent:
- Adapts queries based on actual profile content
- Can decide to search differently if early results are poor
- Makes smart scraping decisions (skip login walls, prioritize fresh postings)
- Can be improved by improving the prompt — no code changes needed

### Why SearXNG + Scrapling (not direct API)?
- LinkedIn/Indeed/Glassdoor don't offer free job search APIs
- SearXNG aggregates multiple search engines → more job URLs from diverse sources
- Scrapling provides local open-source HTTP, dynamic-browser, and stealth fetchers
- This combo gives strong coverage without a paid scraping API dependency

### Why Celery + Redis instead of cron job?
- Cron runs one process — Celery can run 4+ workers in parallel (one per user)
- Redis queuing means if a worker crashes, tasks are retried
- Easy to scale by adding more workers
- Manual "Scan Now" trigger becomes trivial (just `.delay()`)

### Why PostgreSQL over MongoDB?
- Job relevance scores + profile matching benefits from relational joins
- SQLAlchemy async ORM gives type safety
- JSONB columns give MongoDB-like flexibility where needed (skills, education)

### Why no auth in Phase 1?
- Fastest path to working product
- `user_id` in localStorage is sufficient for single-user testing
- Google OAuth is one FastAPI middleware + one frontend hook in Phase 2
