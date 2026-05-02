# PKJobs — AI-Powered Job Discovery Platform for Pakistan

## Project Purpose
PKJobs is a fullstack AI platform that helps Pakistani professionals find jobs without manually browsing LinkedIn, Indeed, or Rozee. The user fills in their profile once. A ReAct LLM agent then runs daily per user — crafting intelligent search queries, discovering job listings across the web, scraping full job descriptions, scoring relevance, and generating personalized application emails.

**The user never has to leave the platform to find a job. They only leave to apply.**

---

## High-Level Architecture

```
React Frontend
      │
      │ REST / SSE
      ▼
FastAPI Backend
      │
      ├── Profile Service     → stores user background, skills, preferences
      ├── Job Feed Service    → returns scored + ranked jobs per user
      ├── Email Service       → returns LLM-composed application emails
      │
      └── Celery Workers (async)
                │
                └── ReAct Agent Pipeline (runs daily per user)
                          │
                          ├── Step 1: Query Planner    (LLM reads profile → makes search queries)
                          ├── Step 2: SearXNG Search   (runs queries → gets URLs)
                          ├── Step 3: Scrapling Scraper (fetches full JD from URLs)
                          ├── Step 4: JD Parser        (LLM extracts structured info)
                          ├── Step 5: Relevance Scorer (LLM scores job vs profile)
                          └── Step 6: Email Composer   (LLM writes application email if contact found)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + TailwindCSS + Zustand |
| Backend | FastAPI (Python 3.11) |
| Task Queue | Celery + Redis |
| Scheduler | Celery Beat (daily cron per user) |
| Database | PostgreSQL (via SQLAlchemy async) |
| Cache | Redis |
| Search | SearXNG (self-hosted, via Docker) |
| Scraping | Scrapling open-source fetchers |
| LLM | Pluggable via `backend/app/services/llm/base.py` (OpenAI / Anthropic / Ollama) |
| Infrastructure | Docker Compose |

---

## Repository Structure

```
pkjobs/
├── agent.md                          ← YOU ARE HERE
├── frontend/                         ← React app (Vite)
│   ├── agent.md
│   └── src/
│       ├── pages/
│       │   ├── Onboarding/           ← Multi-step profile wizard
│       │   ├── Dashboard/            ← Stats + recent activity
│       │   ├── JobFeed/              ← Creative job discovery UI
│       │   └── EmailDraft/           ← View + copy generated email
│       ├── components/
│       │   ├── JobCard/              ← Individual job card component
│       │   ├── ProfileWizard/        ← Wizard step components
│       │   ├── EmailModal/           ← Email preview modal
│       │   └── common/               ← Buttons, inputs, loaders
│       ├── services/                 ← Axios API wrappers
│       ├── hooks/                    ← Custom React hooks
│       ├── store/                    ← Zustand state
│       └── styles/                   ← Tailwind config + globals
│
├── backend/
│   ├── agent.md
│   └── app/
│       ├── api/
│       │   ├── agent.md
│       │   └── routes/
│       │       ├── profile.py        ← POST /profile, GET /profile/{id}
│       │       ├── jobs.py           ← GET /jobs/{user_id}, POST /jobs/trigger
│       │       └── email.py          ← GET /email/{job_id}
│       ├── services/
│       │   ├── agent.md
│       │   ├── fetcher/              ← ReAct scraping pipeline
│       │   │   ├── agent.md
│       │   │   ├── react_agent.py    ← Main ReAct agent orchestrator
│       │   │   ├── query_planner.py  ← LLM → search queries
│       │   │   ├── searxng_client.py ← SearXNG search wrapper
│       │   │   └── scrapling_client.py← Scrapling scrape wrapper
│       │   ├── parser/
│       │   │   ├── agent.md
│       │   │   ├── jd_extractor.py   ← LLM extracts structured JD fields
│       │   │   └── email_finder.py   ← Finds contact email in JD
│       │   ├── llm/
│       │   │   ├── agent.md
│       │   │   ├── base.py           ← Abstract LLM interface
│       │   │   ├── openai_provider.py
│       │   │   ├── anthropic_provider.py
│       │   │   └── email_composer.py ← Generates application emails
│       │   └── scheduler/
│       │       ├── agent.md
│       │       └── daily_runner.py   ← Celery Beat task per user
│       ├── models/
│       │   ├── agent.md
│       │   ├── user.py
│       │   ├── profile.py
│       │   ├── job.py
│       │   └── email_draft.py
│       ├── workers/
│       │   ├── agent.md
│       │   └── celery_app.py
│       ├── core/
│       │   ├── config.py             ← All env vars + settings
│       │   └── logging.py
│       └── db/
│           ├── session.py            ← Async DB session
│           └── base.py               ← SQLAlchemy base
│
├── infra/
│   ├── agent.md
│   ├── docker-compose.yml
│   └── searxng/
│       └── settings.yml
│
└── docs/
    ├── agent.md
    └── flow.md                       ← Full user + system flow
```

---

## Key Concepts for Codex

### 1. ReAct Agent Pattern
The core intelligence lives in `backend/app/services/fetcher/react_agent.py`.
It follows: **Thought → Action → Observation → Thought → ...** loop.
- **Thought**: LLM reasons about what to do next
- **Action**: Run SearXNG query OR scrape URL OR score job
- **Observation**: Result of the action
- Loop continues until agent decides it has enough jobs (default: 15-20 per user)

### 2. LLM is Pluggable
Never hardcode an LLM provider. Always go through `backend/app/services/llm/base.py`.
The `BaseLLMProvider` interface has: `complete(prompt: str) -> str` and `complete_json(prompt: str, schema: dict) -> dict`.

### 3. Profile Drives Everything
The `UserProfile` model is the most important DB model. Every agent decision starts by reading the user's profile. Profile fields: `title`, `skills[]`, `experience_years`, `education`, `preferred_locations[]`, `preferred_job_types[]`, `industries[]`, `salary_range`, `languages[]`.

### 4. Job Sources (No Restrictions)
SearXNG searches across ALL engines. Primary targets:
- LinkedIn Jobs, Indeed, Glassdoor (international)
- Rozee.pk, Mustakbil.com, Bayt.com (Pakistan/regional)
- Company career pages (direct)
- The agent decides which URLs are worth scraping based on result quality.

### 5. No Auth (Phase 1)
Authentication is intentionally excluded in Phase 1. User is identified by `user_id` UUID. Auth (Google OAuth) comes in Phase 2.

---

## Running the Project

```bash
# 1. Start infrastructure
cd infra && docker-compose up -d

# 2. Backend
cd backend
pip install -r requirements.txt
scrapling install   # required for Scrapling dynamic/stealth browser fetchers
uvicorn app.main:app --reload --port 8000

# 3. Celery Worker
cd backend
celery -A app.workers.celery_app worker --loglevel=info

# 4. Celery Beat (scheduler)
cd backend
celery -A app.workers.celery_app beat --loglevel=info

# 5. Frontend
cd frontend
npm install && npm run dev
```

---

## Environment Variables (backend/.env)
```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/pkjobs
REDIS_URL=redis://localhost:6379/0
SEARXNG_URL=http://localhost:8888
SCRAPLING_FETCH_MODE=auto
SCRAPLING_HEADLESS=true
SCRAPLING_TIMEOUT_MS=30000
SCRAPLING_WAIT_MS=1000
SCRAPLING_SOLVE_CLOUDFLARE=false
SCRAPLING_PROXY=
LLM_PROVIDER=openai          # or "anthropic" or "ollama"
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Current Phase: Phase 1
- [x] Architecture defined
- [ ] Profile onboarding flow
- [ ] ReAct agent pipeline
- [ ] Job feed UI
- [ ] Email composer
- [ ] Daily scheduler
