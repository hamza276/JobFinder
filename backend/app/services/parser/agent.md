# Parser Service - JD Extraction

## Purpose
Parser services convert scraped job page text into structured fields used by quality gates, scoring, storage, and email composition.

## `jd_extractor.py`
`JDExtractor.extract(text, url)` uses the configured LLM provider to return an `ExtractedJob` dataclass:

```python
@dataclass
class ExtractedJob:
    title: str | None
    company: str | None
    location: str | None
    job_type: str | None
    salary_range: str | None
    posted_date_raw: str | None
    posted_at: datetime | None
    description_clean: str
    description_short: str
    required_skills: list[str]
    contact_email: str | None
    is_valid_job: bool
```

## Current Behavior
- Pages shorter than 100 characters are rejected before calling the LLM.
- LLM output must be valid JSON.
- If the LLM fails or returns a non-object response, the extractor uses a conservative local fallback that can recover title/company from the job URL or obvious page text.
- The fallback rejects login walls, 404/expired pages, and pages without clear job signals.
- Extracted emails are regex-validated before saving.
- Required skills are cleaned and de-duplicated.
- Relative dates such as `today`, `yesterday`, `2 days ago`, `3 weeks ago`, and `1 month ago` are parsed.
- `ExtractedJob.to_dict()` serializes `posted_at` so downstream scoring prompts and tests can consume it safely.

## Quality Contract
Extraction should be factual and conservative. If the page is a login wall, 404, expired job, generic search page, or not a job listing, set `is_valid_job=False`.

## Notes For Future Changes
- Do not store hallucinated emails.
- Keep `description_clean` job-specific and avoid boilerplate.
- If this module changes, update this `agent.md` and the parser tests in the same task.
