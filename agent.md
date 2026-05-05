# PKJobs - AI-Powered Job Discovery Platform for Pakistan

## Project Purpose
PKJobs is a pure AI-as-a-service job discovery product for Pakistani professionals. It helps users find jobs without manually browsing LinkedIn, Indeed, Rozee, and company career pages. A user fills in their profile once. A ReAct-style LLM pipeline then runs per user, builds search queries, discovers jobs, scrapes job descriptions, scores relevance, and generates application emails.

The user stays inside the platform for discovery and leaves only when they decide to apply.
Frame this codebase as an AI-enabled SaaS job discovery product.

## Current Runtime Setup
- Python: 3.13.1
- Root virtual environment: `.venv`
- Root Python dependency file: `requirements.txt`
- Backend environment file: `backend/.env`
- Active LLM provider: `groq`
- Active LLM model: `llama-3.3-70b-versatile`
- Groq key is stored locally in `backend/.env`; never copy real API keys into tracked docs or examples.

## High-Level Architecture

```text
React frontend
  REST API
FastAPI backend
  Profile service
  Job feed service
  Email service
  Celery workers
    ReAct job pipeline
      Query planning with LLM
      SearXNG search
      Hosted Scrapling page fetch
      JD parsing with LLM
      Relevance scoring with LLM
      Email composition with LLM
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, TailwindCSS, Zustand |
| Backend | FastAPI, Python 3.13.1 |
| Task queue | Celery, Redis |
| Scheduler | Celery Beat |
| Database | PostgreSQL, SQLAlchemy async, Alembic |
| Cache | Redis |
| Search | SearXNG |
| Scraping | Hosted Scrapling REST API |
| LLM | Groq by default, pluggable via `backend/app/services/llm/base.py` |
| Infrastructure | Docker Compose |

## Repository Structure

```text
pkjobs/
  agent.md
  requirements.txt
  frontend/
    agent.md
    package.json
    src/
      pages/
      components/
      services/
      hooks/
      store/
      styles/
  backend/
    agent.md
    requirements.txt
    .env.example
    app/
      main.py
      api/routes/
      core/
        config.py
        logging.py
      db/
      models/
      services/
        fetcher/
        llm/
          base.py
          email_composer.py
        parser/
        scheduler/
      workers/
        celery_app.py
    alembic/
  infra/
    docker-compose.yml
    searxng/
  docs/
    flow.md
```

## LLM Rules
- All LLM calls must go through `backend/app/services/llm/base.py`.
- Do not import Groq, Anthropic, or any LLM SDK directly from routes, workers, or business services.
- The default provider is `GroqProvider`.
- The default model is `llama-3.3-70b-versatile`.
- `LLM_PROVIDER`, `LLM_MODEL`, and provider API keys are read through `backend/app/core/config.py`.

## Environment Variables

`backend/.env` should include:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pkjobs
REDIS_URL=redis://localhost:6379/0
SEARXNG_URL=https://searxngapp.app.digitalsgalaxy.com

SCRAPLING_FETCH_MODE=auto
SCRAPLING_API_URL=https://scraplingbackend.app.digitalsgalaxy.com
SCRAPLING_HEADLESS=true
SCRAPLING_TIMEOUT_MS=30000
SCRAPLING_WAIT_MS=1000
SCRAPLING_RETRIES=2
SCRAPLING_SOLVE_CLOUDFLARE=false
SCRAPLING_PROXY=

LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile
REACT_AGENT_MAX_JOBS=20
REACT_AGENT_MAX_ITER=40
REACT_AGENT_MAX_SEARCHES=8
REACT_AGENT_MAX_SCRAPES=14
REACT_AGENT_SCAN_TIMEOUT_SECONDS=600
REACT_AGENT_MIN_RELEVANCE_SCORE=0.55
REACT_AGENT_MAX_JOB_AGE_DAYS=90
REACT_AGENT_SEARCH_RESULTS_PER_QUERY=20
GROQ_API_KEY=your_key_here
ANTHROPIC_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434

CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

## Running The Project

From the project root:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Start infrastructure:

```powershell
cd infra
docker-compose up -d
```

Start backend:

```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

Start Celery worker:

```powershell
cd backend
celery -A app.workers.celery_app worker --loglevel=info
```

Start Celery Beat:

```powershell
cd backend
celery -A app.workers.celery_app beat --loglevel=info
```

Start frontend:

```powershell
cd frontend
npm install
npm run dev
```

Scraping runs through the hosted Scrapling REST API. No local Scrapling browser install is required for normal app runs.

## Test And Verification Commands

Backend unit tests:

```powershell
cd backend
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Backend syntax check:

```powershell
cd backend
..\.venv\Scripts\python.exe -m compileall app tests
```

Python dependency check:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pip check
```

Frontend lint and production build:

```powershell
cd frontend
npm.cmd run lint
npm.cmd run build
```

## Engineering Notes
- Services should stay framework-light. Do not pass FastAPI request or response objects into services.
- Database operations should use async SQLAlchemy sessions.
- Celery tasks should remain thin and delegate to service functions.
- Runtime files, virtual environments, temp folders, and secrets must stay untracked.
- Frontend API access should stay inside `frontend/src/services/`.

## Current Phase
- [x] Architecture defined
- [x] Groq configured as default LLM provider
- [x] Python 3.13.1 root `.venv` created
- [x] Root `requirements.txt` added
- [x] Profile onboarding flow
- [x] ReAct agent pipeline
- [x] Job feed UI
- [x] Email composer
- [x] Daily scheduler
- [x] Backend unit test suite
- [x] Frontend lint/build verification
