import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
import re
from urllib.parse import unquote, urlparse

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

    def to_dict(self) -> dict:
        data = asdict(self)
        if self.posted_at:
            data["posted_at"] = self.posted_at.isoformat()
        return data


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
            return self._fallback_extract(text, url)
        if isinstance(data, list):
            data = next((item for item in data if isinstance(item, dict)), {})
        if not isinstance(data, dict):
            return self._fallback_extract(text, url)

        job = ExtractedJob(
            title=data.get("title"),
            company=data.get("company"),
            location=data.get("location"),
            job_type=data.get("job_type"),
            salary_range=data.get("salary_range"),
            posted_date_raw=data.get("posted_date_raw"),
            description_clean=data.get("description_clean", ""),
            description_short=data.get("description_short", ""),
            required_skills=self._clean_skills(data.get("required_skills", [])),
            contact_email=self._validate_email(data.get("contact_email")),
            is_valid_job=data.get("is_valid_job", True),
        )
        job.posted_at = self._parse_posted_date(job.posted_date_raw)
        return job

    def _fallback_extract(self, text: str, url: str) -> ExtractedJob:
        """Conservative local extraction for LLM outage/rate-limit paths."""
        clean_text = self._clean_description(text)
        lower_text = clean_text.lower()
        if self._looks_invalid_page(lower_text):
            return ExtractedJob(is_valid_job=False)

        title, company = self._title_company_from_url(url)
        if not title:
            title = self._title_from_text(clean_text)
        if not company:
            company = self._company_from_text(clean_text, title)

        if not title or not company or not self._has_job_signal(lower_text, url):
            return ExtractedJob(is_valid_job=False)

        job = ExtractedJob(
            title=title,
            company=company,
            location=self._location_from_text(lower_text),
            job_type=self._job_type_from_text(lower_text),
            posted_date_raw=self._posted_date_from_text(lower_text),
            description_clean=clean_text[:1000],
            description_short=self._short_description(clean_text),
            required_skills=self._skills_from_text(lower_text),
            contact_email=self._validate_email(self._email_from_text(clean_text)),
            is_valid_job=True,
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
            if "yesterday" in raw_lower:
                return now - timedelta(days=1)
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

    def _clean_skills(self, value) -> list[str]:
        if not value:
            return []
        if isinstance(value, str):
            value = value.split(",")
        cleaned = []
        seen = set()
        for item in value:
            text = str(item).strip()
            key = text.lower()
            if text and key not in seen:
                cleaned.append(text)
                seen.add(key)
        return cleaned

    def _looks_invalid_page(self, lower_text: str) -> bool:
        invalid_terms = [
            "page not found",
            "404",
            "job no longer available",
            "job expired",
            "sign in to view",
            "login to view",
            "create an account to view",
        ]
        return any(term in lower_text for term in invalid_terms)

    def _has_job_signal(self, lower_text: str, url: str) -> bool:
        signals = ["job", "role", "apply", "hiring", "developer", "engineer", "requirements"]
        return any(signal in lower_text for signal in signals) or "/jobs/" in url.lower()

    def _title_company_from_url(self, url: str) -> tuple[str | None, str | None]:
        parsed = urlparse(url)
        slug = unquote(parsed.path.rstrip("/").split("/")[-1])
        if not slug or slug.isdigit():
            return None, None
        slug = re.sub(r"\b\d{5,}\b.*$", "", slug)
        slug = re.sub(r"[-_]+", " ", slug).strip()
        if not slug:
            return None, None

        title = None
        company = None
        at_match = re.match(r"(.+?)\s+at\s+(.+)$", slug, flags=re.IGNORECASE)
        if at_match:
            title = self._title_case(at_match.group(1))
            company = self._title_case(at_match.group(2))
        else:
            title = self._title_case(slug)

        return self._clean_title(title), self._clean_company(company)

    def _title_from_text(self, text: str) -> str | None:
        patterns = [
            r"(?:hiring|looking for|job opening for)\s+(?:a|an)?\s*([A-Za-z0-9 +#./-]{3,80})",
            r"\b((?:Senior|Sr\.?|Junior|Jr\.?|Lead|Principal)?\s*(?:Frontend|Front-End|Full Stack|Full-Stack|Backend|Python|React|Next\.js|JavaScript|Software)\s+(?:Developer|Engineer))\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return self._clean_title(self._title_case(match.group(1)))
        return None

    def _company_from_text(self, text: str, title: str | None) -> str | None:
        if title:
            escaped = re.escape(title)
            match = re.search(rf"{escaped}\s+(?:at|with)\s+([A-Za-z0-9 &.,'-]{{2,70}})", text, flags=re.IGNORECASE)
            if match:
                return self._clean_company(self._title_case(match.group(1)))
        patterns = [
            r"(?:company|employer|organization)\s*[:\-]\s*([A-Za-z0-9 &.,'-]{2,70})",
            r"\bat\s+([A-Z][A-Za-z0-9 &.,'-]{2,70})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return self._clean_company(self._title_case(match.group(1)))
        return None

    def _location_from_text(self, lower_text: str) -> str | None:
        locations = [
            "karachi",
            "lahore",
            "islamabad",
            "rawalpindi",
            "faisalabad",
            "peshawar",
            "quetta",
            "multan",
            "hyderabad",
            "pakistan",
            "remote",
        ]
        found = [self._title_case(location) for location in locations if location in lower_text]
        if not found:
            return None
        if "Remote" in found and "Pakistan" in found:
            return "Remote, Pakistan"
        return ", ".join(dict.fromkeys(found[:3]))

    def _job_type_from_text(self, lower_text: str) -> str | None:
        if "part-time" in lower_text or "part time" in lower_text:
            return "part-time"
        if "contract" in lower_text:
            return "contract"
        if "remote" in lower_text:
            return "remote"
        if "full-time" in lower_text or "full time" in lower_text:
            return "full-time"
        return None

    def _posted_date_from_text(self, lower_text: str) -> str | None:
        match = re.search(r"\b(?:just now|today|yesterday|\d+\s+(?:hour|day|week|month)s?\s+ago)\b", lower_text)
        return match.group(0) if match else None

    def _skills_from_text(self, lower_text: str) -> list[str]:
        skills = [
            "React",
            "Next.js",
            "TypeScript",
            "JavaScript",
            "Node.js",
            "Python",
            "Django",
            "FastAPI",
            "SQL",
            "PostgreSQL",
            "Tailwind CSS",
            "REST APIs",
            "GraphQL",
            "AWS",
            "Docker",
            "Git",
        ]
        found = []
        for skill in skills:
            key = skill.lower()
            aliases = {
                "next.js": ["nextjs"],
                "node.js": ["nodejs"],
                "tailwind css": ["tailwind"],
                "rest apis": ["rest api", "restful"],
            }.get(key, [])
            if key in lower_text or any(alias in lower_text for alias in aliases):
                found.append(skill)
        return found

    def _email_from_text(self, text: str) -> str | None:
        match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        return match.group(0) if match else None

    def _clean_description(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def _short_description(self, text: str) -> str:
        parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        return " ".join(parts[:2])[:400]

    def _clean_title(self, title: str | None) -> str | None:
        if not title:
            return None
        title = re.sub(r"\bjobs?\b.*$", "", title, flags=re.IGNORECASE).strip(" -|,")
        return title[:100] or None

    def _clean_company(self, company: str | None) -> str | None:
        if not company:
            return None
        company = re.sub(r"\b(?:job|jobs|careers|apply|hiring)\b.*$", "", company, flags=re.IGNORECASE)
        company = company.strip(" -|,")
        return company[:100] or None

    def _title_case(self, value: str) -> str:
        return " ".join(part if part.isupper() else part.capitalize() for part in str(value).split())
