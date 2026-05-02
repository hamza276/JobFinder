import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import re

from app.services.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

EXTRACT_SYSTEM = """You are a job listing data extractor.
Extract structured information from raw job listing webpage text.
Respond ONLY with valid JSON. No preamble, no backticks."""

EXTRACT_PROMPT = """Extract job listing information from this webpage text.

TEXT:
{text}

Return JSON with these exact fields:
{{
  "title": "job title or null",
  "company": "company name or null",
  "location": "city/country or null",
  "job_type": "full-time|part-time|remote|contract|null",
  "salary_range": "salary info as string or null",
  "posted_date_raw": "original posting date string or null",
  "description_clean": "main job description without boilerplate (max 1000 chars)",
  "description_short": "2-sentence summary of the role",
  "required_skills": ["skill1", "skill2"],
  "contact_email": "email@domain.com or null",
  "is_valid_job": true/false
}}

Set is_valid_job=false if the page is a 404, login wall, expired job, or not a job listing."""


@dataclass
class ExtractedJob:
    title: str | None = None
    company: str | None = None
    location: str | None = None
    job_type: str | None = None
    salary_range: str | None = None
    posted_date_raw: str | None = None
    posted_at: datetime | None = None
    description_clean: str = ""
    description_short: str = ""
    required_skills: list[str] = field(default_factory=list)
    contact_email: str | None = None
    is_valid_job: bool = True


class JDExtractor:
    def __init__(self, llm: BaseLLMProvider):
        self.llm = llm

    async def extract(self, text: str, url: str) -> ExtractedJob:
        if not text or len(text) < 100:
            return ExtractedJob(is_valid_job=False)

        prompt = EXTRACT_PROMPT.format(text=text[:5000])
        try:
            data = await self.llm.complete_json(prompt=prompt, system=EXTRACT_SYSTEM)
        except Exception as e:
            logger.error(f"JD extraction failed for {url}: {e}")
            return ExtractedJob(is_valid_job=False)

        job = ExtractedJob(
            title=data.get("title"),
            company=data.get("company"),
            location=data.get("location"),
            job_type=data.get("job_type"),
            salary_range=data.get("salary_range"),
            posted_date_raw=data.get("posted_date_raw"),
            description_clean=data.get("description_clean", ""),
            description_short=data.get("description_short", ""),
            required_skills=data.get("required_skills", []),
            contact_email=self._validate_email(data.get("contact_email")),
            is_valid_job=data.get("is_valid_job", True),
        )
        job.posted_at = self._parse_posted_date(job.posted_date_raw)
        return job

    def _validate_email(self, email: str | None) -> str | None:
        """Validate LLM-extracted email with regex to catch hallucinations."""
        if not email:
            return None
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return email if re.match(pattern, email.strip()) else None

    def _parse_posted_date(self, raw: str | None) -> datetime | None:
        if not raw:
            return None
        raw_lower = raw.lower().strip()
        now = datetime.utcnow()
        try:
            if "just now" in raw_lower or "today" in raw_lower:
                return now
            if "hour" in raw_lower:
                hours = int(re.search(r'(\d+)', raw_lower).group(1))
                return now - timedelta(hours=hours)
            if "day" in raw_lower:
                days = int(re.search(r'(\d+)', raw_lower).group(1))
                return now - timedelta(days=days)
            if "week" in raw_lower:
                weeks = int(re.search(r'(\d+)', raw_lower).group(1))
                return now - timedelta(weeks=weeks)
            if "month" in raw_lower:
                months = int(re.search(r'(\d+)', raw_lower).group(1))
                return now - timedelta(days=months * 30)
            # Try direct date parse
            from dateutil import parser as dateparser
            return dateparser.parse(raw)
        except Exception:
            return None
