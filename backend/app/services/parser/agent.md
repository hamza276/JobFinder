# Parser Service — JD Extraction + Email Finding

## Purpose
Takes raw scraped text from a job listing page and extracts structured, clean information.

## `jd_extractor.py`
Uses LLM to extract structured fields from raw scraped text.

Input: `raw_text: str` (full scraped page content)
Output: `ExtractedJob` dataclass

```python
@dataclass
class ExtractedJob:
    title: str | None
    company: str | None
    location: str | None
    job_type: str | None          # full-time / part-time / remote / contract
    salary_range: str | None      # raw string, e.g. "PKR 80,000 - 120,000/month"
    posted_date_raw: str | None   # raw string, e.g. "3 days ago" or "April 28, 2024"
    posted_at: datetime | None    # parsed from posted_date_raw
    description_clean: str        # cleaned JD without boilerplate
    description_short: str        # 2-sentence summary (LLM generated)
    required_skills: list[str]    # extracted skills list
    contact_email: str | None     # if found
    is_valid_job: bool            # False if page was a 404, login wall, etc.
```

LLM Prompt Strategy:
- System: "You are a data extraction specialist. Extract job listing information from the provided webpage text."
- Return JSON matching the ExtractedJob schema
- If a field cannot be found, use null (not empty string)
- `is_valid_job = False` if text contains "sign in to view", "404", "job no longer available"

## `email_finder.py`
Separate, simpler function. Uses regex FIRST (fast), falls back to LLM if needed.

```python
def find_contact_email(text: str) -> str | None:
    """
    1. Try regex: looks for email patterns in text
    2. If regex finds nothing but text mentions "email your CV" or "send resume to",
       use LLM to extract the email from context
    3. Returns None if no email found
    """
```

Regex patterns to try:
- Standard email: `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`
- With "to:" prefix: `(?:to|email|send to|apply to|contact)\s*:?\s*([a-zA-Z0-9._%+-]+@...)`
- HR patterns: `hr@`, `careers@`, `jobs@`, `recruitment@`, `hiring@`

## Notes for Codex
- `jd_extractor.py` should cache results in Redis (key: `jd:{url_hash}`) to avoid re-parsing same URL
- Cache TTL: 24 hours
- Always validate extracted email with regex before saving — LLMs hallucinate email addresses
- `posted_at` parsing: if "3 days ago" → `datetime.now() - timedelta(days=3)`
