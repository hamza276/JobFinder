# Frontend — React + Vite + TailwindCSS

## Purpose
The React frontend is a single-page application. It has 4 main views:
1. **Onboarding** — multi-step wizard to collect user profile
2. **Dashboard** — shows stats: jobs found today, jobs viewed, emails generated
3. **JobFeed** — the main experience: a creative "newspaper meets card deck" job discovery UI
4. **EmailDraft** — shows LLM-generated email for a specific job with copy/edit options

## Stack
- React 18 + Vite
- TailwindCSS (utility classes only, no component libraries)
- Zustand (global state: user profile, jobs list, selected job)
- Axios (API calls to FastAPI backend at `http://localhost:8000`)
- React Router v6

## Design Philosophy
**NOT a typical job board.**
The JobFeed is intentionally designed to feel like a **morning newspaper** — jobs are "stories", each card has a headline (job title), a lede (1-line summary), and a "read more" expand. Think: NYT homepage meets a job board.
Colors: deep navy + cream + gold accents. Typography: serif for titles, sans for body.

## Key Pages

### `/onboarding`
Multi-step wizard. Steps:
1. Basic info (name, current title, years of experience)
2. Skills (tag input, autocomplete)
3. Education (degree, field, institution)
4. Job preferences (locations, job types, salary range)
5. Industries of interest
Submits to `POST /api/profile` → redirects to `/dashboard`

### `/dashboard`
Shows:
- "Last scan: X hours ago" + "Next scan: in Y hours"
- Stats cards: jobs found, viewed, emails generated
- Quick link to JobFeed
- Manual "Scan Now" button → `POST /api/jobs/trigger`

### `/feed`
The main UI. Jobs shown as cards in a masonry/newspaper layout.
- Each card: Company logo (fallback to initials), Job Title, Company, Location, Posted date, 2-line snippet of JD
- Click → expands into full JD drawer (right side panel)
- Inside drawer: full JD, "Generate Email" button, "Open Original" link
- Visual indicator: relevance score shown as a colored bar (green=high, yellow=medium)

### `/email/:jobId`
Full-page email view:
- "To:" field (pre-filled if email found in JD)
- "Subject:" (generated)
- Body (generated, editable textarea)
- "Copy Email" button
- "Back to Feed" link

## State (Zustand Store)
```
store/
  useProfileStore.js    → { profile, setProfile }
  useJobsStore.js       → { jobs, selectedJob, setSelectedJob, markViewed }
  useEmailStore.js      → { emails, fetchEmail, getEmail }
  useUIStore.js         → { isDrawerOpen, isScanRunning, setDrawerOpen }
```

## API Service Layer (`src/services/`)
```
api.js              → Axios instance with base URL
profileService.js   → createProfile(), getProfile()
jobsService.js      → getJobs(), triggerScan(), markJobViewed()
emailService.js     → getEmail(jobId), regenerateEmail(jobId)
```

## Folder Conventions
- Each page folder has: `index.jsx` (main component) + `components/` subfolder if needed
- Each component folder has: `index.jsx` + optional `*.module.css` if Tailwind isn't enough
- No default exports on utilities/services — always named exports

## Running
```bash
cd frontend
npm install
npm run dev       # starts at http://localhost:5173
npm run build     # production build
```

## Important Notes for Codex
- Backend runs at `http://localhost:8000` in dev. Use `VITE_API_BASE_URL` env var.
- No auth headers needed in Phase 1. Pass `user_id` as query param or store in localStorage.
- All API errors should be caught and shown as toast notifications (use a simple custom hook `useToast`).
- The job feed should support **infinite scroll** — load 10 jobs at a time.
