# Backend - FastAPI Service

## Purpose
The backend exposes REST APIs, manages persistence, and orchestrates Celery scans for the pure AI-as-a-service job discovery product.

## Stack
- Python 3.13.1
- FastAPI
- SQLAlchemy async ORM with asyncpg
- Alembic migrations
- Celery + Redis
- Pydantic v2
- Groq LLM provider via `app/services/llm/base.py`
- Hosted Scrapling REST API + SearXNG for discovery

## Key Modules
- `app/main.py`: FastAPI app, CORS, router registration, startup DB check.
- `app/core/config.py`: all environment-backed settings.
- `app/api/routes/profile.py`: onboarding/profile CRUD.
- `app/api/routes/jobs.py`: feed, stats, manual scan trigger, viewed/hidden updates.
- `app/api/routes/email.py`: email draft generation and regeneration.
- `app/services/fetcher/`: search, scrape, quality gates, calibrated scoring.
- `app/services/parser/`: LLM-backed JD extraction.
- `app/services/scheduler/`: scan orchestration and persistence.
- `app/workers/celery_app.py`: Celery worker and beat tasks.

## Important Conventions
1. Services stay framework-light; do not pass FastAPI request/response objects into services.
2. DB operations are async and use SQLAlchemy sessions.
3. Celery tasks stay thin and delegate to scheduler services.
4. All LLM calls go through `services/llm/base.py`.
5. Search/scoring quality changes must update `app/services/fetcher/agent.md`.
6. Any module behavior change must update the nearest relevant `agent.md` during the same task.

## Production Quality Settings
Configured through `.env` and `app/core/config.py`:

```env
REACT_AGENT_MAX_JOBS=20
REACT_AGENT_MAX_ITER=40
REACT_AGENT_MAX_SEARCHES=8
REACT_AGENT_MAX_SCRAPES=14
REACT_AGENT_SCAN_TIMEOUT_SECONDS=600
REACT_AGENT_MIN_RELEVANCE_SCORE=0.55
REACT_AGENT_MAX_JOB_AGE_DAYS=3
REACT_AGENT_SEARCH_RESULTS_PER_QUERY=20
SCRAPLING_RETRIES=2
SCRAPLING_API_URL=https://scraplingbackend.app.digitalsgalaxy.com
SEARXNG_URL=https://searxngapp.app.digitalsgalaxy.com
```

These limits keep scans bounded for SaaS reliability while still allowing enough search/scrape coverage for useful results.

## Running
```powershell
cd backend
..\.venv\Scripts\python.exe -m pip install -r ..\requirements.txt
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Worker:

```powershell
cd backend
..\.venv\Scripts\celery.exe -A app.workers.celery_app worker --loglevel=info --concurrency=4
```

Beat:

```powershell
cd backend
..\.venv\Scripts\celery.exe -A app.workers.celery_app beat --loglevel=info
```

## Verification
```powershell
cd backend
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
..\.venv\Scripts\python.exe -m compileall app tests
..\.venv\Scripts\python.exe -m pip check
```
