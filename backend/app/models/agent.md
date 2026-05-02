# Models — SQLAlchemy ORM

## Database: PostgreSQL (async via asyncpg)

## Models

### `user.py` — User
```
users table:
  id            UUID PRIMARY KEY
  created_at    TIMESTAMP
  updated_at    TIMESTAMP
```
Phase 1: minimal. No auth. Just an ID to tie profile + jobs together.

### `profile.py` — UserProfile
```
user_profiles table:
  id                  UUID PRIMARY KEY
  user_id             UUID FK → users.id
  full_name           VARCHAR(255)
  current_title       VARCHAR(255)         ← e.g. "React Developer"
  experience_years    INTEGER
  skills              JSONB                ← ["React", "TypeScript", "Node.js"]
  education           JSONB                ← {degree, field, institution, year}
  preferred_locations JSONB                ← ["Karachi", "Remote", "Lahore"]
  preferred_job_types JSONB                ← ["full-time", "remote", "contract"]
  industries          JSONB                ← ["FinTech", "E-commerce"]
  salary_min          INTEGER              ← PKR per month
  salary_max          INTEGER
  languages           JSONB                ← ["English", "Urdu"]
  bio                 TEXT                 ← optional short bio
  created_at          TIMESTAMP
  updated_at          TIMESTAMP
```
**This is the most important model.** The ReAct agent reads this to make all decisions.

### `job.py` — Job
```
jobs table:
  id                UUID PRIMARY KEY
  user_id           UUID FK → users.id       ← which user this was found for
  
  # Source info
  source_url        VARCHAR(1024) UNIQUE     ← original job posting URL
  source_platform   VARCHAR(100)             ← "linkedin", "indeed", "rozee", "direct"
  
  # Job details (extracted by LLM)
  title             VARCHAR(255)
  company           VARCHAR(255)
  location          VARCHAR(255)
  job_type          VARCHAR(100)             ← "full-time", "remote", etc.
  salary_range      VARCHAR(255)             ← raw string as found in JD
  posted_at         TIMESTAMP                ← when job was posted (parsed from JD)
  
  # Content
  description_raw   TEXT                     ← full raw JD text
  description_short VARCHAR(500)             ← 2-line summary (LLM generated)
  contact_email     VARCHAR(255)             ← if found in JD, else NULL
  
  # Scoring
  relevance_score   FLOAT                    ← 0.0 to 1.0, LLM scored
  relevance_reason  TEXT                     ← LLM explanation for score
  
  # Status
  is_viewed         BOOLEAN DEFAULT FALSE
  is_hidden         BOOLEAN DEFAULT FALSE    ← user dismissed this job
  
  fetched_at        TIMESTAMP                ← when we scraped it
  created_at        TIMESTAMP
```

### `email_draft.py` — EmailDraft
```
email_drafts table:
  id            UUID PRIMARY KEY
  job_id        UUID FK → jobs.id
  user_id       UUID FK → users.id
  to_email      VARCHAR(255)    ← NULL if no contact found
  subject       VARCHAR(500)
  body          TEXT
  is_regenerated BOOLEAN DEFAULT FALSE
  created_at    TIMESTAMP
```

## Relationships
- User → has one UserProfile
- User → has many Jobs (found for them)
- Job → has one EmailDraft (generated lazily, not upfront)

## Notes for Codex
- Use `mapped_column` and `Mapped` types (SQLAlchemy 2.0 style)
- All models inherit from `app.db.base.Base`
- UUIDs generated server-side via `uuid.uuid4()`
- JSONB fields use `JSON` type in SQLAlchemy with `postgresql_using="jsonb"`
- Run migrations with Alembic: `alembic revision --autogenerate -m "description"`
