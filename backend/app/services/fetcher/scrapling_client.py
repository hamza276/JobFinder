import asyncio
import logging
import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ScrapedPage:
    url: str
    text_content: str
    html: str
    success: bool
    error: str | None = None
    status_code: int | None = None
    fetcher: str | None = None


JS_HEAVY_SITES = ["glassdoor.com", "linkedin.com", "indeed.com"]
PROTECTED_SITES = ["linkedin.com", "glassdoor.com", "indeed.com", "rozee.pk"]
STRATEGY_ENDPOINTS = {
    "http": "/api/v1/http",
    "dynamic": "/api/v1/dynamic",
    "stealth": "/api/v1/stealthy",
}


class ScraplingClient:
    """Hosted Scrapling REST API client.

    The ReAct agent keeps calling `scrape(url) -> ScrapedPage`, but scraping now
    runs through the hosted backend instead of local Scrapling browser fetchers.
    """

    def __init__(self):
        self.base_url = settings.SCRAPLING_API_URL.rstrip("/")
        self.mode = settings.SCRAPLING_FETCH_MODE.lower()
        self.timeout_ms = settings.SCRAPLING_TIMEOUT_MS
        self.timeout_seconds = max(1, int(self.timeout_ms / 1000))
        self.wait_ms = settings.SCRAPLING_WAIT_MS
        self.proxy = settings.SCRAPLING_PROXY or None

    async def scrape(self, url: str, retries: int = 3) -> ScrapedPage:
        last_error = ""
        strategies = self._strategies_for_url(url)

        for attempt in range(retries):
            for strategy in strategies:
                try:
                    logger.debug(
                        "Hosted Scrapling scrape attempt %s/%s via %s: %s",
                        attempt + 1,
                        retries,
                        strategy,
                        url,
                    )
                    data = await self._fetch(url, strategy)
                    status = int(data.get("status") or 0)
                    if status >= 400:
                        raise RuntimeError(f"HTTP {status}")

                    html = self._extract_html(data)
                    text = self._clean_text(self._html_to_text(html))
                    if len(text) < 80:
                        raise RuntimeError("Hosted Scrapling returned too little text")

                    return ScrapedPage(
                        url=str(data.get("url") or url),
                        text_content=text,
                        html=html,
                        success=True,
                        status_code=status,
                        fetcher=strategy,
                    )

                except Exception as exc:
                    last_error = f"{strategy}: {exc}"
                    logger.warning("Hosted Scrapling %s failed for %s: %s", strategy, url, exc)
                    if "HTTP 404" in str(exc):
                        return ScrapedPage(
                            url=url,
                            text_content="",
                            html="",
                            success=False,
                            error=last_error,
                            status_code=404,
                            fetcher=strategy,
                        )

            if attempt < retries - 1:
                await asyncio.sleep(2**attempt)

        return ScrapedPage(
            url=url,
            text_content="",
            html="",
            success=False,
            error=last_error or "Max retries exceeded",
        )

    async def _fetch(self, url: str, strategy: str) -> dict:
        endpoint = STRATEGY_ENDPOINTS[strategy]
        payload = self._build_payload(url, strategy)
        timeout = httpx.Timeout(self.timeout_seconds + 10)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{self.base_url}{endpoint}", json=payload)
            response.raise_for_status()
            data = response.json()

        if not isinstance(data, dict):
            raise RuntimeError("Hosted Scrapling returned a non-object response")
        return data

    def _build_payload(self, url: str, strategy: str) -> dict:
        payload = {
            "url": url,
            "extraction_type": "html",
            "main_content_only": False,
        }

        if strategy == "http":
            payload.update(
                {
                    "timeout": self.timeout_seconds,
                    "retries": 1,
                    "retry_delay": 1,
                    "follow_redirects": "safe",
                    "stealthy_headers": True,
                    "impersonate": "chrome",
                }
            )
            if self.proxy:
                payload["proxy"] = self.proxy
            return payload

        payload.update(
            {
                "headless": settings.SCRAPLING_HEADLESS,
                "google_search": True,
                "wait": self.wait_ms,
                "timeout": self.timeout_ms,
                "disable_resources": True,
                "network_idle": True,
            }
        )
        if self.proxy:
            payload["proxy"] = self.proxy
        if strategy == "stealth":
            payload.update(
                {
                    "solve_cloudflare": settings.SCRAPLING_SOLVE_CLOUDFLARE,
                    "block_webrtc": True,
                    "hide_canvas": True,
                }
            )
        return payload

    def _strategies_for_url(self, url: str) -> list[str]:
        if self.mode in {"http", "dynamic", "stealth"}:
            return [self.mode]

        domain = self._get_domain(url)
        if any(site in domain for site in PROTECTED_SITES):
            return ["stealth", "dynamic", "http"]
        if any(site in domain for site in JS_HEAVY_SITES):
            return ["dynamic", "http"]
        return ["http", "dynamic"]

    def _extract_html(self, data: dict) -> str:
        content = data.get("content") or []
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(str(item) for item in content if item)
        return str(content or "")

    def _html_to_text(self, html: str) -> str:
        text = re.sub(r"(?is)<(script|style|nav|footer|header|aside|iframe|noscript).*?>.*?</\1>", " ", html)
        text = re.sub(r"(?is)<br\s*/?>", " ", text)
        text = re.sub(r"(?is)</p>|</div>|</li>|</h[1-6]>", " ", text)
        text = re.sub(r"(?is)<[^>]+>", " ", text)
        return unescape(text)

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()[:8000]

    def _get_domain(self, url: str) -> str:
        return urlparse(url).netloc.lower()
