# Fetcher Service - Job Discovery Pipeline

## Purpose
This service finds, fetches, validates, scores, and ranks jobs for a user profile. It is the quality-critical part of PKJobs because it decides which jobs enter the feed.

## Current Files
- `react_agent.py`: orchestrates search, scrape, extraction, deterministic quality gates, LLM scoring, and final ranking.
- `searxng_client.py`: calls SearXNG, de-duplicates URLs, rejects generic home/index pages, and marks useful detail/category pages as job-like candidates.
- `scrapling_client.py`: calls the hosted Scrapling REST API and returns cleaned text/HTML using the existing `ScrapedPage` contract.
- `quality.py`: deterministic production quality rules for URL type, location eligibility, seniority fit, freshness, skill overlap, and score calibration.

## ReAct Flow
The LLM can still choose `search`, `scrape`, or `finish`, but the application owns the final quality checks.

```text
UserProfile
  -> deterministic seed search, then fallback and LLM-guided search queries
  -> SearXNG candidates
  -> scrape candidate page
  -> if aggregate/search page: extract detail job URLs and queue them
  -> auto-scrape queued detail candidates before asking the LLM for more search guidance
  -> JD extraction
  -> deterministic quality assessment
  -> LLM relevance score
  -> heuristic score fallback if LLM scoring is unavailable or rate-limited
  -> calibrated score and threshold gate
  -> ScoredJob list sorted by relevance
```

## Quality Rules
- Do not save aggregate/search/category URLs as final jobs.
- Do not spend scrape budget on generic root/index URLs such as job-board homepages or bare `/jobs` pages.
- Prefer accessible sources such as Mustakbil, Rozee, Bayt, company career pages, and broad non-LinkedIn searches because LinkedIn currently returns signup walls through the hosted scraper.
- Stop spending scrape budget on one failing domain after repeated scrape/invalid-page failures; move to the next available source.
- Prefer detail URLs such as LinkedIn `/jobs/view/...`, Rozee job pages, Mustakbil job pages, company apply pages, and similar detail pages.
- Reject jobs missing title or company.
- Reject postings older than `REACT_AGENT_MAX_JOB_AGE_DAYS`; default is 3 days for latest-only scans.
- Reject jobs with missing posting dates because max-3-days freshness cannot be verified.
- Reject remote jobs that are tied to a foreign country unless the text indicates worldwide/APAC/global/Pakistan eligibility.
- Cap scores for seniority mismatch, e.g. principal/staff/lead roles for low-experience profiles.
- Cap scores for role mismatch, e.g. full-stack/backend roles for a frontend profile.
- Cap scores for job-type mismatch, e.g. part-time roles for a full-time-only profile.
- Cap or reduce scores when skill overlap is weak or job description text is too thin.
- Store jobs only when calibrated relevance is at least `REACT_AGENT_MIN_RELEVANCE_SCORE`.

## Settings
Configured in `backend/app/core/config.py` and `.env`:

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

## Notes For Future Changes
- Keep LLM prompts narrow; never let the LLM bypass `quality.py`.
- The agent should remain usable when Groq is rate-limited: deterministic seed searches, fallback searches, parser fallback, and heuristic scoring must keep scans from hard failing.
- Hosted Scrapling 404s should fail fast instead of trying every dynamic strategy.
- Update tests in `backend/tests/test_react_agent.py`, `test_fetcher_clients.py`, and quality-specific tests whenever scoring or URL rules change.
- If this module changes, update this `agent.md` in the same task.
