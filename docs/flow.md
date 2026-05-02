# PKJobs — Complete System Flow

## User Journey

### First Visit (Onboarding)
1. User opens `http://localhost:5173`
2. Routed to `/onboarding`
3. Completes 5-step wizard:
   - Step 1: Name, current title, years of experience
   - Step 2: Skills (tag input, e.g. "React, TypeScript, Node.js")
   - Step 3: Education (degree, field, university)
   - Step 4: Preferred locations, job types, salary range
   - Step 5: Industries
4. On submit → `POST /api/profile` → returns `{ user_id, profile_id }`
5. `user_id` stored in `localStorage` (no auth in Phase 1)
6. Redirected to `/dashboard`

### Dashboard
- Shows: "Your profile is set! First scan runs at 6 AM."
- "Scan Now" button → `POST /api/jobs/trigger` → Celery task dispatched immediately
- After scan: shows stats card (jobs found, viewed, emails ready)

### Job Feed (`/feed`)
- `GET /api/jobs/{user_id}?page=1&limit=10`
- Jobs displayed as newspaper-style cards
- Sorted by `relevance_score DESC`, then `fetched_at DESC`
- Infinite scroll: loads next page when user reaches bottom
- Click on card → right drawer opens with full JD + buttons

### Job Detail Drawer
- Full job description
- "🔗 View Original" → opens `source_url` in new tab
- "✉️ Generate Email" → `GET /api/email/{job_id}`
  - If email already generated: shows it instantly
  - If not: triggers generation (few seconds), shows loading
- "✕ Hide Job" → `PATCH /api/jobs/{job_id}/viewed` + hide from feed

### Email View
- "To:" field (pre-filled or empty)
- "Subject:" (generated)
- Body textarea (editable by user)
- "📋 Copy Email" button
- "🔄 Regenerate" → `POST /api/email/{job_id}/regenerate`

---

## Daily Scan Flow (System)

```
06:00 AM PKT
    │
    ▼
Celery Beat fires: scan_all_users task
    │
    ▼
Load all user IDs from DB
    │
    ├─► scan_user_jobs(user_id_1) → Celery queue
    ├─► scan_user_jobs(user_id_2) → Celery queue
    └─► scan_user_jobs(user_id_N) → Celery queue

Each scan_user_jobs task:
    │
    ▼
Load UserProfile from DB
    │
    ▼
Initialize ReActJobAgent(llm, searxng, scrapling, extractor)
    │
    ▼
agent.run(profile) → ReAct Loop
    │
    │  [Thought] LLM decides: "I should search for React jobs in Karachi"
    │  [Action] search("React developer jobs Karachi 2024 site:linkedin.com")
    │  [Observation] Found 8 job listing URLs...
    │
    │  [Thought] "This LinkedIn URL looks good, let me scrape it"
    │  [Action] scrape("https://linkedin.com/jobs/view/...")
    │  [Observation] Scraped. Job: Senior React Developer at TechCorp. Skills: React, Redux...
    │
    │  [Thought] "This matches the profile well. Let me score it."
    │  [Action] score({title: "Senior React Dev", skills: ["React", "Redux"], ...})
    │  [Observation] Score: 0.87. Reason: Strong skill match, Karachi location...
    │
    │  ... continues for 8-10 iterations
    │
    │  [Thought] "I have 18 jobs. That's enough."
    │  [Action] finish()
    │
    ▼
Returns List[ScoredJob] (sorted by score)
    │
    ▼
save_jobs_to_db() → PostgreSQL
    │
    ▼
generate_emails_for_new_jobs() → For jobs with contact emails
    │
    ▼
Done. User sees new jobs next time they open the feed.
```

---

## Data Flow Summary

```
SearXNG → URLs
Scrapling → Raw text
LLM (extractor) → Structured ExtractedJob
LLM (scorer) → relevance_score (0-1)
PostgreSQL → Stored Job records
LLM (composer) → EmailDraft
React Frontend → Displays to user
```
