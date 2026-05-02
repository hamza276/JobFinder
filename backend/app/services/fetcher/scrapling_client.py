import asyncio
import logging
import re
from dataclasses import dataclass
from urllib.parse import urlparse

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


class ScraplingClient:
    """Local open-source page scraper powered by Scrapling.

    The client keeps the ReAct agent's `scrape(url) -> ScrapedPage`
    contract while using Scrapling's local fetchers.
    """

    def __init__(self):
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
                        "Scrapling scrape attempt %s/%s via %s: %s",
                        attempt + 1,
                        retries,
                        strategy,
                        url,
                    )
                    page = await self._fetch(url, strategy)
                    status = getattr(page, "status", None)
                    if status and status >= 400:
                        raise RuntimeError(f"HTTP {status} {getattr(page, 'reason', '')}".strip())

                    text = self._extract_text(page)
                    html = self._extract_html(page)
                    if len(text) < 80:
                        raise RuntimeError("Scrapling returned too little text")

                    return ScrapedPage(
                        url=url,
                        text_content=text,
                        html=html,
                        success=True,
                        status_code=status,
                        fetcher=strategy,
                    )

                except Exception as exc:
                    last_error = f"{strategy}: {exc}"
                    logger.warning("Scrapling %s failed for %s: %s", strategy, url, exc)

            if attempt < retries - 1:
                await asyncio.sleep(2**attempt)

        return ScrapedPage(
            url=url,
            text_content="",
            html="",
            success=False,
            error=last_error or "Max retries exceeded",
        )

    async def _fetch(self, url: str, strategy: str):
        try:
            from scrapling.fetchers import AsyncFetcher, DynamicFetcher, StealthyFetcher
        except ImportError as exc:
            raise RuntimeError(
                "Scrapling is not installed. Run `pip install -r backend/requirements.txt`."
            ) from exc

        if strategy == "http":
            kwargs = self._proxy_kwargs()
            return await AsyncFetcher.get(
                url,
                timeout=self.timeout_seconds,
                retries=1,
                retry_delay=1,
                impersonate="chrome",
                stealthy_headers=True,
                follow_redirects="safe",
                selector_config={"huge_tree": True},
                **kwargs,
            )

        browser_kwargs = {
            "headless": settings.SCRAPLING_HEADLESS,
            "disable_resources": True,
            "network_idle": True,
            "load_dom": True,
            "timeout": self.timeout_ms,
            "wait": self.wait_ms,
            "retries": 1,
            "retry_delay": 1,
            "block_ads": True,
            "selector_config": {"huge_tree": True},
            **self._proxy_kwargs(),
        }

        if strategy == "dynamic":
            return await DynamicFetcher.async_fetch(url, **browser_kwargs)

        if strategy == "stealth":
            return await StealthyFetcher.async_fetch(
                url,
                solve_cloudflare=settings.SCRAPLING_SOLVE_CLOUDFLARE,
                block_webrtc=True,
                hide_canvas=True,
                **browser_kwargs,
            )

        raise ValueError(f"Unknown Scrapling fetch strategy: {strategy}")

    def _strategies_for_url(self, url: str) -> list[str]:
        if self.mode in {"http", "dynamic", "stealth"}:
            return [self.mode]

        domain = self._get_domain(url)
        if any(site in domain for site in PROTECTED_SITES):
            return ["stealth", "dynamic", "http"]
        if any(site in domain for site in JS_HEAVY_SITES):
            return ["dynamic", "http"]
        return ["http", "dynamic"]

    def _proxy_kwargs(self) -> dict[str, str]:
        return {"proxy": self.proxy} if self.proxy else {}

    def _extract_text(self, page) -> str:
        try:
            text = page.get_all_text(
                separator=" ",
                strip=True,
                ignore_tags=(
                    "script",
                    "style",
                    "nav",
                    "footer",
                    "header",
                    "aside",
                    "iframe",
                    "noscript",
                ),
            )
        except Exception:
            text = getattr(page, "text", "") or ""
        return self._clean_text(str(text))

    def _extract_html(self, page) -> str:
        try:
            return str(page.get())
        except Exception:
            body = getattr(page, "body", b"")
            encoding = getattr(page, "encoding", "utf-8") or "utf-8"
            if isinstance(body, bytes):
                return body.decode(encoding, errors="ignore")
            return str(body)

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()[:8000]

    def _get_domain(self, url: str) -> str:
        return urlparse(url).netloc.lower()
