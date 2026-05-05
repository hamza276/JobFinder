# API Routes

## Conventions
- All routes return Pydantic response models (never raw dicts)
- All routes use `async def`
- DB session injected via `Depends(get_db)` from `api/deps.py`
- Errors raised as `HTTPException` with descriptive detail messages
- All routes prefixed with `/api` in `main.py`

## Route Files
- `profile.py` → router prefix: `/profile`
- `jobs.py` → router prefix: `/jobs`
- `email.py` → router prefix: `/email`

## Response Models Pattern
Each route file defines its own Pydantic response/request schemas at the top.
Example:
```python
class ProfileCreateRequest(BaseModel):
    full_name: str
    current_title: str
    experience_years: int
    skills: list[str]
    ...

class ProfileResponse(BaseModel):
    id: str
    user_id: str
    full_name: str
    ...
    model_config = ConfigDict(from_attributes=True)
```

## CORS
Configured in `main.py` from `app/core/config.py`.
In dev: allow both `http://localhost:5173` and `http://127.0.0.1:5173` because Vite may be opened through either hostname.
In prod: restrict to actual frontend domain.

## Current API Quality Notes
- Profile payloads clean duplicate string-list values and reject invalid salary ranges.
- Job feed results are sorted by calibrated relevance score, then fetch time.
- Manual scan trigger uses Redis cooldown and queues Celery work instead of blocking the request.
- If route schemas or validation behavior changes, update this `agent.md` during the same task.
