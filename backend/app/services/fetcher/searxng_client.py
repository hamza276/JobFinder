import httpx
import logging
from dataclasses import dataclass
from urllib.parse import urlparse

from app.core.config import settings

logger = logging.getLogger(__name__)

JOB_LISTING_PATTERNS = [
    "/jobs/", "/job/", "/careers/", "/career/", "/vacancy/",
    "job-detail", "jobdetail", "apply", "posting",
    "rozee.pk/job", "mustakbil.com", "bayt.com/en/jobs",
    "linkedin.com/jobs/view", "indeed.com/viewjob",
    "glassdoor.com/job-listing",
]

NON_JOB_PATTERNS = [
    "wikipedia.org", "youtube.com", "facebook.com", "twitter.com",
    "/news/", "/article/", "/blog/", "reddit.com",
]


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str
    is_job_listing: bool


class SearXNGClient:
    def __init__(self):
        self.base_url = settings.SEARXNG_URL
        self.client = httpx.AsyncClient(timeout=15)

    async def search(self, query: str, num_results: int = 10) -> list[SearchResult]:
        """Search via SearXNG and return filtered results."""
        params = {
            "q": query,
            "format": "json",
            "pageno": 1,
        }
        try:
            resp = await self.client.get(f"{self.base_url}/search", params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"SearXNG search failed for query '{query}': {e}")
            return []

        results = []
        for item in data.get("results", [])[:num_results]:
            url = item.get("url", "")
            title = item.get("title", "")
            snippet = item.get("content", "")
            source = self._extract_source(url)
            is_job = self._is_job_listing(url, title, snippet)

            results.append(SearchResult(
                title=title,
                url=url,
                snippet=snippet,
                source=source,
                is_job_listing=is_job,
            ))

        logger.info(f"SearXNG: '{query}' → {len(results)} results, {sum(1 for r in results if r.is_job_listing)} job listings")
        return results

    def _is_job_listing(self, url: str, title: str, snippet: str) -> bool:
        url_lower = url.lower()
        combined = (url_lower + " " + title.lower() + " " + snippet.lower())

        # Hard exclude non-job sites
        for pattern in NON_JOB_PATTERNS:
            if pattern in url_lower:
                return False

        # Check URL patterns
        for pattern in JOB_LISTING_PATTERNS:
            if pattern in url_lower:
                return True

        # Check title/snippet keywords
        job_keywords = ["apply now", "job description", "we are hiring", "requirements:",
                        "responsibilities:", "qualifications:", "salary:", "pkr", "full-time", "remote"]
        return any(kw in combined for kw in job_keywords)

    def _extract_source(self, url: str) -> str:
        try:
            domain = urlparse(url).netloc.lower()
            if "linkedin" in domain: return "linkedin"
            if "indeed" in domain: return "indeed"
            if "glassdoor" in domain: return "glassdoor"
            if "rozee" in domain: return "rozee"
            if "mustakbil" in domain: return "mustakbil"
            if "bayt" in domain: return "bayt"
            return domain.replace("www.", "").split(".")[0]
        except Exception:
            return "unknown"

    async def close(self):
        await self.client.aclose()
