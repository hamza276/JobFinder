# Backend — FastAPI (Python 3.11)

## Purpose
The FastAPI backend exposes REST APIs for the frontend, manages the database, and orchestrates the Celery workers that run the ReAct agent pipeline.

## Stack
- FastAPI 0.110+
- SQLAlchemy 2.0 (async ORM)
- asyncpg (PostgreSQL async driver)
- Alembic (migrations)
- Celery 5.x + Redis (task queue)
- Pydantic v2 (request/response validation)

## Entry Point
`app/main.py` — creates FastAPI app, includes all routers, sets up CORS, connects DB.

## Directory Map
```
app/
├── main.py               ← FastAPI app entry point
├── api/
│   ├── deps.py           ← Shared FastAPI dependencies (get_db, get_current_user)
│   └── routes/
│       ├── profile.py    ← /api/profile
│       ├── jobs.py       ← /api/jobs
│       └── email.py      ← /api/email
├── services/             ← Business logic (no FastAPI dependencies here)
├── models/               ← SQLAlchemy ORM models
├── db/
│   ├── session.py        ← async_sessionmaker
│   └── base.py           ← declarative_base
├── workers/
│   └── celery_app.py     ← Celery + Beat configuration
└── core/
    ├── config.py         ← Pydantic Settings (reads .env)
    └── logging.py        ← Structured logging setup
```

## API Endpoints

### Profile
| Method | Path | Description |
|---|---|---|
| POST | `/api/profile` | Create user profile (onboarding) |
| GET | `/api/profile/{user_id}` | Fetch user profile |
| PATCH | `/api/profile/{user_id}` | Update profile fields |

### Jobs
| Method | Path | Description |
|---|---|---|
| GET | `/api/jobs/{user_id}` | Get paginated jobs for user (latest first) |
| POST | `/api/jobs/trigger` | Manually trigger scan for user |
| PATCH | `/api/jobs/{job_id}/viewed` | Mark job as viewed |
| GET | `/api/jobs/{user_id}/stats` | Get stats (total found, viewed, etc.) |

### Email
| Method | Path | Description |
|---|---|---|
| GET | `/api/email/{job_id}` | Get generated email for a job |
| POST | `/api/email/{job_id}/regenerate` | Regenerate email with LLM |

## Important Conventions
1. **Services are pure Python** — no FastAPI/Request objects inside services. Only called from routes.
2. **All DB operations are async** — use `async with session` pattern everywhere.
3. **Celery tasks are thin** — they call service functions, not implement logic themselves.
4. **LLM calls always go through `services/llm/base.py`** — never call OpenAI/Anthropic SDK directly from other services.
5. **Config via environment** — all secrets from `.env` via `core/config.py` Settings class.

## Running
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
scrapling install       # required for Scrapling dynamic/stealth browser fetchers

# DB migrations
alembic upgrade head

# Start API
uvicorn app.main:app --reload --port 8000

# Start Celery worker (separate terminal)
celery -A app.workers.celery_app worker --loglevel=info --concurrency=4

# Start Celery Beat scheduler (separate terminal)
celery -A app.workers.celery_app beat --loglevel=info
```
