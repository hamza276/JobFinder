import logging
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.services.fetcher.quality import is_aggregate_url, is_detail_job_url, normalize_url

logger = logging.getLogger(__name__)

JOB_LISTING_PATTERNS = [
    "/jobs/",
    "/job/",
    "/careers/",
    "/career/",
    "/vacancy/",
    "job-detail",
    "jobdetail",
    "apply",
    "posting",
    "rozee.pk/job",
    "mustakbil.com",
    "bayt.com/en/jobs",
    "linkedin.com/jobs/view",
    "indeed.com/viewjob",
    "glassdoor.com/job-listing",
]

NON_JOB_PATTERNS = [
    "linkedin.com",
    "wikipedia.org",
    "youtube.com",
    "facebook.com",
    "twitter.com",
    "/news/",
    "/article/",
    "/blog/",
    "reddit.com",
]

GENERIC_INDEX_PATHS = {
    "",
    "/",
    "/jobs",
    "/jobs/",
    "/careers",
    "/careers/",
    "/remote-jobs",
    "/remote-jobs/",
}


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
        """Search via SearXNG and return de-duplicated job-like results."""
        pages = max(1, min(3, (num_results + 9) // 10))
        raw_items = []

        for page in range(1, pages + 1):
            params = {"q": query, "format": "json", "pageno": page}
            try:
                resp = await self.client.get(f"{self.base_url}/search", params=params)
                resp.raise_for_status()
                raw_items.extend(resp.json().get("results", []))
            except Exception as exc:
                logger.error("SearXNG search failed for query '%s' page %s: %s", query, page, exc)
                break

        results: list[SearchResult] = []
        seen: set[str] = set()
        for item in raw_items:
            url = normalize_url(item.get("url", ""))
            if not url or url in seen:
                continue
            seen.add(url)

            title = item.get("title", "")
            snippet = item.get("content", "")
            source = self._extract_source(url)
            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source=source,
                    is_job_listing=self._is_job_listing(url, title, snippet),
                )
            )
            if len(results) >= num_results:
                break

        logger.info(
            "SearXNG: '%s' -> %s results, %s job-like results",
            query,
            len(results),
            sum(1 for result in results if result.is_job_listing),
        )
        return results

    def _is_job_listing(self, url: str, title: str, snippet: str) -> bool:
        parsed = urlparse(url)
        url_lower = url.lower()
        combined = f"{url_lower} {title.lower()} {snippet.lower()}"

        if any(pattern in url_lower for pattern in NON_JOB_PATTERNS):
            return False

        if self._is_generic_index_url(parsed):
            return False

        if is_detail_job_url(url_lower) or is_aggregate_url(url_lower):
            return True

        if any(pattern in url_lower for pattern in JOB_LISTING_PATTERNS):
            return True

        job_keywords = [
            "apply now",
            "job description",
            "we are hiring",
            "requirements:",
            "responsibilities:",
            "qualifications:",
            "salary:",
            "pkr",
            "full-time",
            "remote",
        ]
        return any(keyword in combined for keyword in job_keywords)

    def _is_generic_index_url(self, parsed) -> bool:
        path = (parsed.path or "/").lower()
        domain = parsed.netloc.lower()
        if path in {"", "/"}:
            return True
        if parsed.query:
            return False
        if path in GENERIC_INDEX_PATHS and any(
            board in domain
            for board in [
                "linkedin.",
                "indeed.",
                "glassdoor.",
                "weworkremotely.com",
                "crossover.com",
                "remoteok.com",
                "remotive.com",
            ]
        ):
            return True
        return False

    def _extract_source(self, url: str) -> str:
        try:
            domain = urlparse(url).netloc.lower()
            if "linkedin" in domain:
                return "linkedin"
            if "indeed" in domain:
                return "indeed"
            if "glassdoor" in domain:
                return "glassdoor"
            if "rozee" in domain:
                return "rozee"
            if "mustakbil" in domain:
                return "mustakbil"
            if "bayt" in domain:
                return "bayt"
            return domain.replace("www.", "").split(".")[0]
        except Exception:
            return "unknown"

    async def close(self):
        await self.client.aclose()
