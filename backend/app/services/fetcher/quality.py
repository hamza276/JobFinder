import re
from dataclasses import dataclass, field
from datetime import datetime
from html import unescape
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from app.models.profile import UserProfile
from app.services.parser.jd_extractor import ExtractedJob


PAKISTAN_TERMS = {
    "pakistan",
    "karachi",
    "lahore",
    "islamabad",
    "rawalpindi",
    "faisalabad",
    "peshawar",
    "quetta",
    "multan",
    "hyderabad",
    "sindh",
    "punjab",
}

REMOTE_OPEN_TERMS = {
    "worldwide",
    "anywhere",
    "global",
    "globally",
    "apac",
    "asia pacific",
    "asia",
    "emea",
    "mena",
    "pakistan",
}

FOREIGN_LOCATION_TERMS = {
    "poland",
    "united states",
    "usa",
    "u.s.",
    "canada",
    "united kingdom",
    "uk",
    "germany",
    "france",
    "india",
    "australia",
    "netherlands",
    "spain",
    "portugal",
    "brazil",
    "mexico",
}

AGGREGATE_URL_PATTERNS = [
    r"linkedin\.[^/]+/jobs/(?!view)(?:[^/?#]+-jobs|search)",
    r"linkedin\.[^/]+/jobs/?(?:\?|$)",
    r"glassdoor\.[^/]+/Job/[^?#]+-jobs-",
    r"indeed\.[^/]+/jobs(?:\?|/)?",
    r"rozee\.pk/job/jsearch",
    r"remoterocketship\.com/jobs/[^/]+/?$",
    r"bayt\.com/.*/jobs/[^/]+/?$",
]

DETAIL_URL_PATTERNS = [
    r"linkedin\.[^/]+/jobs/view/",
    r"indeed\.[^/]+/viewjob",
    r"glassdoor\.[^/]+/job-listing/",
    r"rozee\.pk/job/",
    r"mustakbil\.com/jobs/job/",
    r"bayt\.com/.*/jobs/.+/\d+",
    r"applytojob\.com/apply/",
]


@dataclass
class QualityAssessment:
    accepted: bool
    score_cap: float = 1.0
    score_multiplier: float = 1.0
    reasons: list[str] = field(default_factory=list)


def normalize_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return str(url or "").strip()

    query = parse_qs(parsed.query, keep_blank_values=False)
    kept = {
        key: value
        for key, value in query.items()
        if not key.lower().startswith("utm_")
        and key.lower()
        not in {
            "trk",
            "ref",
            "refid",
            "trackingid",
            "source",
            "position",
            "page",
        }
    }
    clean_query = urlencode(kept, doseq=True)
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or "/",
            "",
            clean_query,
            "",
        )
    )


def is_aggregate_url(url: str) -> bool:
    normalized = normalize_url(url).lower()
    return any(re.search(pattern, normalized) for pattern in AGGREGATE_URL_PATTERNS)


def is_detail_job_url(url: str) -> bool:
    normalized = normalize_url(url).lower()
    if is_aggregate_url(normalized):
        return False
    return any(re.search(pattern, normalized) for pattern in DETAIL_URL_PATTERNS)


def extract_job_urls(base_url: str, html: str, text: str = "", limit: int = 20) -> list[str]:
    haystack = unescape(f"{html or ''}\n{text or ''}")
    urls: list[str] = []

    patterns = [
        r"https?://[^\s\"'<>]+",
        r"href=[\"']([^\"']+)[\"']",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, haystack, flags=re.IGNORECASE):
            candidate = match.group(1) if match.lastindex else match.group(0)
            candidate = candidate.replace("&amp;", "&")
            if candidate.startswith("/"):
                candidate = urljoin(base_url, candidate)
            normalized = normalize_url(candidate)
            if is_detail_job_url(normalized) and normalized not in urls:
                urls.append(normalized)
            if len(urls) >= limit:
                return urls

    for match in re.finditer(r"currentJobId=(\d+)", haystack, flags=re.IGNORECASE):
        parsed = urlparse(base_url)
        if "linkedin" in parsed.netloc.lower():
            candidate = f"{parsed.scheme}://{parsed.netloc}/jobs/view/{match.group(1)}"
            normalized = normalize_url(candidate)
            if normalized not in urls:
                urls.append(normalized)
            if len(urls) >= limit:
                return urls

    return urls


def assess_job_quality(
    profile: UserProfile,
    job: ExtractedJob,
    source_url: str,
    *,
    now: datetime | None = None,
    max_age_days: int = 3,
) -> QualityAssessment:
    now = now or datetime.utcnow()
    reasons: list[str] = []
    score_cap = 1.0
    multiplier = 1.0

    if is_aggregate_url(source_url):
        return QualityAssessment(False, 0.0, 0.0, ["source URL is a search/category page"])

    if not job.title or not job.company:
        return QualityAssessment(False, 0.0, 0.0, ["missing title or company"])

    description = (
        f"{job.title or ''} {job.company or ''} {job.location or ''} "
        f"{job.job_type or ''} {source_url or ''} {job.description_clean or ''} {job.description_short or ''}"
    )
    normalized_text = _normalize(description)

    if not _has_location_fit(profile, job, normalized_text):
        return QualityAssessment(False, 0.35, 0.5, ["location is not eligible for the user's Pakistan/remote preference"])

    if not job.posted_at:
        return QualityAssessment(False, 0.4, 0.5, ["posting date is missing; latest-only scans require a date"])

    age_days = max(0, (now - job.posted_at.replace(tzinfo=None)).days)
    if age_days > max_age_days:
        return QualityAssessment(False, 0.35, 0.5, [f"posting is older than {max_age_days} days"])
    reasons.append(f"posting is within {max_age_days} days")

    seniority_cap = _seniority_score_cap(profile.experience_years, normalized_text)
    if seniority_cap < 1.0:
        score_cap = min(score_cap, seniority_cap)
        reasons.append("seniority appears above profile experience")

    role_cap = _role_alignment_score_cap(profile.current_title, normalized_text)
    if role_cap < 1.0:
        score_cap = min(score_cap, role_cap)
        reasons.append("role focus differs from profile title")

    job_type_cap = _job_type_score_cap(profile.preferred_job_types or [], normalized_text)
    if job_type_cap < 1.0:
        score_cap = min(score_cap, job_type_cap)
        reasons.append("job type does not match profile preferences")

    overlap = _skill_overlap(profile.skills or [], job.required_skills or [], normalized_text)
    if profile.skills and overlap == 0:
        score_cap = min(score_cap, 0.55)
        multiplier *= 0.75
        reasons.append("no clear overlap with profile skills")
    elif overlap >= 3:
        multiplier *= 1.05
        reasons.append("strong skill overlap")
    elif overlap >= 1:
        reasons.append("some skill overlap")

    if not job.description_clean and not job.description_short:
        score_cap = min(score_cap, 0.6)
        multiplier *= 0.8
        reasons.append("thin job description")

    return QualityAssessment(True, score_cap, min(multiplier, 1.1), reasons)


def calibrated_score(llm_score: float, assessment: QualityAssessment) -> float:
    score = max(0.0, min(1.0, float(llm_score or 0.0)))
    score *= assessment.score_multiplier
    score = min(score, assessment.score_cap)
    return round(max(0.0, min(1.0, score)), 3)


def _has_location_fit(profile: UserProfile, job: ExtractedJob, normalized_text: str) -> bool:
    preferred = {_normalize(item) for item in (profile.preferred_locations or [])}
    location_text = _normalize(job.location or "")
    combined = f"{location_text} {normalized_text}"

    if any(term in combined for term in PAKISTAN_TERMS):
        return True

    if any(term and term != "remote" and term in combined for term in preferred):
        return True

    if "remote" not in combined:
        return False

    foreign_location = any(term in location_text for term in FOREIGN_LOCATION_TERMS)
    location_explicitly_open = any(term in location_text for term in REMOTE_OPEN_TERMS)
    if foreign_location and not location_explicitly_open:
        return False

    if any(term in combined for term in REMOTE_OPEN_TERMS):
        return True

    return "remote" in preferred


def _seniority_score_cap(experience_years: int, normalized_text: str) -> float:
    required_years = _required_years(normalized_text)
    if required_years and experience_years + 1 < required_years:
        return 0.55

    if any(term in normalized_text for term in ["principal", "staff engineer", "engineering manager", "architect"]):
        return 0.45 if experience_years < 7 else 1.0
    if any(term in normalized_text for term in ["lead ", "team lead", "head of"]):
        return 0.6 if experience_years < 6 else 1.0
    if any(term in normalized_text for term in ["senior", "sr."]):
        return 0.7 if experience_years < 4 else 1.0
    return 1.0


def _required_years(text: str) -> int | None:
    matches = re.findall(r"(\d{1,2})\s*\+?\s*(?:years|yrs|year)", text)
    if not matches:
        return None
    return max(int(match) for match in matches)


def _role_alignment_score_cap(profile_title: str, normalized_text: str) -> float:
    title = _normalize(profile_title)
    if "frontend" in title or "front-end" in title or "front end" in title:
        if any(term in normalized_text for term in ["frontend", "front-end", "front end", "react", "next.js", "nextjs"]):
            if any(term in normalized_text for term in ["full stack", "full-stack", "backend", "back-end", "java engineer"]):
                return 0.78
            return 1.0
        if any(term in normalized_text for term in ["backend", "back-end", "java", "python engineer", "devops"]):
            return 0.45

    if "backend" in title or "back-end" in title or "back end" in title:
        if any(term in normalized_text for term in ["frontend", "front-end", "front end"]) and "backend" not in normalized_text:
            return 0.55

    return 1.0


def _job_type_score_cap(preferred_job_types: list[str], normalized_text: str) -> float:
    preferred = {_normalize(item) for item in preferred_job_types if item}
    if "part-time" in normalized_text or "part time" in normalized_text:
        if "part-time" not in preferred and "part time" not in preferred:
            return 0.55
    if "contract" in normalized_text and "contract" not in preferred:
        return 0.75
    return 1.0


def _skill_overlap(profile_skills: list[str], required_skills: list[str], normalized_text: str) -> int:
    normalized_profile = {_normalize(skill) for skill in profile_skills if skill}
    normalized_required = {_normalize(skill) for skill in required_skills if skill}
    overlap = normalized_profile.intersection(normalized_required)

    aliases = {
        "javascript": ["js", "ecmascript"],
        "typescript": ["ts"],
        "react": ["reactjs", "react.js"],
        "next.js": ["nextjs", "next"],
        "tailwind css": ["tailwind"],
    }
    for skill in normalized_profile:
        if skill in normalized_text:
            overlap.add(skill)
        for alias in aliases.get(skill, []):
            if alias in normalized_text:
                overlap.add(skill)
    return len(overlap)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()
