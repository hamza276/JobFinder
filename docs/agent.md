# Docs

## Contents
- `flow.md` - complete user journey and system data flow. Read this first if you're new to the project.

## Key Design Decisions

### Why ReAct Agent Instead Of Simple Scheduled Scraper?
A fixed scraper with hardcoded queries quickly becomes stale. The ReAct agent:
- Adapts queries based on actual profile content.
- Can decide to search differently if early results are poor.
- Makes scraping decisions such as skipping login walls and prioritizing fresh postings.
- Can be improved through prompts and quality rules without rewriting the entire pipeline.

### Why Hosted SearXNG + Hosted Scrapling Instead Of Direct APIs?
- LinkedIn, Indeed, and Glassdoor do not offer free job search APIs suitable for this product.
- Hosted SearXNG at `https://searxngapp.app.digitalsgalaxy.com` aggregates multiple search engines and gives diverse job URL coverage.
- Hosted Scrapling at `https://scraplingbackend.app.digitalsgalaxy.com` provides HTTP, dynamic-browser, and stealth scraping through a REST API.
- This combination gives strong coverage without a paid scraping API dependency.

### Why Celery + Redis Instead Of Cron?
- Cron runs one process; Celery can run multiple workers in parallel.
- Redis queuing means tasks can be retried if a worker crashes.
- Manual "Scan Now" is easy to queue through `.delay()`.

### Why PostgreSQL Over MongoDB?
- Job relevance scores and profile matching benefit from relational joins.
- SQLAlchemy async ORM gives type safety.
- JSONB columns keep flexibility for skills, education, and other profile data.

### Why No Auth In Phase 1?
- Fastest path to a working product.
- `user_id` in localStorage is sufficient for single-user testing.
- Google OAuth can be added in a later phase.

## Notes
- This is a pure AI-as-a-service job discovery product, not a cybersecurity product.
- If docs behavior guidance changes, update this `agent.md` in the same task.
