# Fetcher Service — ReAct Agent Pipeline

## This is the Heart of PKJobs.
This service is responsible for finding, fetching, and scoring jobs for a user. It runs daily per user via Celery Beat.

## The ReAct Agent Pattern
ReAct = **Re**asoning + **Act**ing. The agent loops through:
```
[Thought] → [Action] → [Observation] → [Thought] → ...
```
Until it reaches a terminal condition (enough jobs found OR max iterations hit).

## Full Pipeline Flow
```
INPUT: UserProfile

ITERATION LOOP (max 10 rounds):
  ┌─────────────────────────────────┐
  │  THOUGHT (LLM)                  │
  │  "I have profile X. I should    │
  │   search for Y because Z."      │
  └──────────────┬──────────────────┘
                 │
  ┌──────────────▼──────────────────┐
  │  ACTION: choose one of:         │
  │  - search(query)                │
  │  - scrape(url)                  │
  │  - score(job_data)              │
  │  - finish()                     │
  └──────────────┬──────────────────┘
                 │
  ┌──────────────▼──────────────────┐
  │  OBSERVATION                    │
  │  Result of the action           │
  │  (URLs, JD text, score, etc.)   │
  └──────────────┬──────────────────┘
                 │
            loop back to THOUGHT

OUTPUT: List[ScoredJob]
```

## Files

### `react_agent.py` — Main Orchestrator
The main class `ReActJobAgent`:
- Takes a `UserProfile` as input
- Maintains a `trajectory` list: all thoughts + actions + observations
- Calls LLM with full trajectory context to get next action
- Dispatches to appropriate tool (SearXNG, Scrapling, scorer)
- Stops when: `finish()` called OR `len(collected_jobs) >= MAX_JOBS` OR `iterations >= MAX_ITER`

```python
class ReActJobAgent:
    MAX_JOBS = 20
    MAX_ITER = 10
    
    async def run(self, profile: UserProfile) -> List[ScoredJob]:
        ...
    
    async def _think_and_act(self, trajectory: list) -> AgentAction:
        # Calls LLM with trajectory, parses action
        ...
    
    async def _execute_action(self, action: AgentAction) -> str:
        # Routes to search/scrape/score
        ...
```

### `query_planner.py` — LLM Query Generator
Given a UserProfile, generates optimized search queries.
These queries are NOT generic — they're crafted to find real job listings.

Example output for a "React Developer, 3 years, Karachi":
```
[
  "React developer jobs Karachi 2024 site:linkedin.com",
  "React frontend engineer Pakistan remote indeed",
  "React Next.js developer Karachi rozee.pk",
  "software engineer React jobs Pakistan apply",
  "frontend developer React Redux Karachi linkedin jobs",
]
```

The LLM is instructed to:
- Generate 5-8 diverse queries per run
- Mix location-specific and remote queries
- Target multiple job boards in the queries
- Include skill synonyms (React → ReactJS, frontend)

### `searxng_client.py` — Search Wrapper
Wraps SearXNG HTTP API.
- `search(query: str, num_results: int = 10) -> List[SearchResult]`
- Returns: title, url, snippet, source_engine
- Filters out results that are clearly NOT job listings (news articles, Wikipedia, etc.)
- Result is a list of candidate URLs to potentially scrape

```python
@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str   # "linkedin", "indeed", "rozee", etc.
    is_job_listing: bool   # Quick heuristic check
```

### `scrapling_client.py` — Page Scraper
Wraps Scrapling fetchers to fetch full page content.
- `scrape(url: str) -> ScrapedPage`
- Uses HTTP fetches for simple pages
- Uses dynamic/stealth browser fetches for JavaScript-heavy or protected pages
- Returns cleaned text content (strips nav, footer, ads)
- Has retry logic (3 attempts with exponential backoff)

```python
@dataclass  
class ScrapedPage:
    url: str
    text_content: str    # cleaned main content
    html: str            # raw HTML for fallback
    success: bool
    error: str | None
```

## Key Design Decisions

1. **Agent context window management**: The trajectory sent to LLM is summarized after 5 iterations to avoid context overflow. `_summarize_trajectory()` method handles this.

2. **Stealth via LLM**: The LLM can decide to "wait" (add random delay) or "skip" a URL based on patterns it recognizes as bot traps. This is NOT programmatic — the LLM makes this call.

3. **Deduplication**: Before storing, each job is checked against `job_url` in the DB. Duplicate URLs are skipped silently.

4. **Pakistan-first scoring**: The relevance scorer gives a +0.2 bonus to jobs that mention Pakistan cities (Karachi, Lahore, Islamabad, Rawalpindi, remote-Pakistan).

5. **Score threshold**: Jobs with `relevance_score < 0.4` are stored but hidden from feed by default.

## LLM Prompt Templates
All prompts are in `prompts/` subfolder (create this):
- `react_system.txt` — System prompt for the ReAct agent
- `query_planner.txt` — Prompt for generating search queries
- `jd_extractor.txt` — Prompt for extracting structured fields from raw JD text
- `relevance_scorer.txt` — Prompt for scoring job vs profile match
- `email_composer.txt` — Prompt for writing application email

## Dependencies
- `searxng_client.py` → needs `SEARXNG_URL` env var
- `scrapling_client.py` → uses `SCRAPLING_*` env vars and local Scrapling fetchers
- `react_agent.py` → needs LLM provider configured
