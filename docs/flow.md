# PKJobs - Complete System Flow

## User Journey

### First Visit
1. User opens the React app.
2. User completes onboarding with name, title, experience, skills, education, preferred locations, job types, salary range, and industries.
3. Frontend calls `POST /api/profile` and stores the returned `user_id`.
4. User lands on the dashboard and can trigger a scan.

### Job Feed
1. Frontend calls `GET /api/jobs/{user_id}`.
2. Jobs are sorted by relevance score and fetch time.
3. User opens a job, reviews the extracted JD, and can open the original source URL.
4. If an email is available or generated, the user can edit/copy the application draft.

## Scan Flow

```text
Celery task
  -> load UserProfile
  -> initialize ReActJobAgent(llm, searxng, hosted_scrapling, extractor)
  -> deterministic seed search
  -> SearXNG candidates
  -> hosted Scrapling scrape via REST API
  -> JD extraction
  -> deterministic quality gates
  -> LLM or heuristic relevance scoring
  -> save new jobs to PostgreSQL
  -> generate email drafts for jobs with contact emails
```

## Data Flow Summary

```text
Hosted SearXNG -> candidate URLs
Hosted Scrapling REST API -> raw HTML and cleaned text
LLM/parser fallback -> structured ExtractedJob
Quality gates -> accepted/capped relevance
LLM/heuristic scorer -> relevance_score
PostgreSQL -> stored job records
LLM email composer -> EmailDraft
React frontend -> user-facing job feed
```

## Notes
- This is a pure AI-as-a-service job discovery product.
- Hosted SearXNG endpoint: `https://searxngapp.app.digitalsgalaxy.com`
- Hosted Scrapling endpoint: `https://scraplingbackend.app.digitalsgalaxy.com`
