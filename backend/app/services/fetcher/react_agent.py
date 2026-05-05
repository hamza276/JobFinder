"""Core job discovery agent.

The LLM chooses search and scrape actions. The application owns execution,
validation, extraction, scoring, and deduplication so a weak LLM step cannot
silently drop good scraped jobs.
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from app.core.config import settings
from app.models.profile import UserProfile
from app.services.fetcher.quality import (
    assess_job_quality,
    calibrated_score,
    extract_job_urls,
    is_aggregate_url,
    normalize_url,
)
from app.services.fetcher.scrapling_client import ScrapedPage, ScraplingClient
from app.services.fetcher.searxng_client import SearchResult, SearXNGClient
from app.services.llm.base import BaseLLMProvider
from app.services.parser.jd_extractor import ExtractedJob, JDExtractor

logger = logging.getLogger(__name__)

VALID_ACTIONS = {"search", "scrape", "score", "finish"}


@dataclass
class AgentAction:
    type: str
    input: dict[str, Any]
    thought: str = ""


@dataclass
class ScoredJob:
    extracted: ExtractedJob
    source_url: str
    source_platform: str
    relevance_score: float
    relevance_reason: str
    fetched_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TrajectoryStep:
    thought: str
    action: AgentAction
    observation: str


REACT_SYSTEM_PROMPT = """You are an intelligent job discovery agent for Pakistani professionals.
Your goal is to find relevant job listings based on the user's profile.

Available actions:
1. search(query: str) - search for job listing URLs using SearXNG
2. scrape(url: str) - scrape one job URL; the app extracts and scores it automatically
3. finish() - stop when enough good matches have been collected

Rules:
- Generate diverse targeted searches across LinkedIn, Indeed, Rozee.pk, Mustakbil, Bayt, and company career pages.
- Only scrape URLs that look like actual job listings.
- Prioritize Pakistan-based jobs and remote roles open to Pakistani candidates.
- Do not scrape the same URL twice.
- Stop once enough relevant jobs are collected or no useful URLs remain.

Always respond with valid JSON only:
{
  "thought": "short reasoning",
  "action": "search|scrape|finish",
  "input": { "query": "...", "url": "..." }
}
"""


class ReActJobAgent:
    """Discovers, scrapes, extracts, scores, and ranks jobs for one user."""

    def __init__(
        self,
        llm: BaseLLMProvider,
        searxng: SearXNGClient,
        scraper: ScraplingClient,
        extractor: JDExtractor,
    ):
        self.llm = llm
        self.searxng = searxng
        self.scraper = scraper
        self.extractor = extractor
        self.max_jobs = settings.REACT_AGENT_MAX_JOBS
        self.max_iter = settings.REACT_AGENT_MAX_ITER
        self.max_searches = settings.REACT_AGENT_MAX_SEARCHES
        self.max_scrapes = settings.REACT_AGENT_MAX_SCRAPES

    async def run(self, profile: UserProfile) -> list[ScoredJob]:
        logger.info("Starting ReAct agent for user %s", profile.user_id)
        trajectory: list[TrajectoryStep] = []
        collected_jobs: list[ScoredJob] = []
        scraped_urls: set[str] = set()
        search_results: dict[str, SearchResult] = {}
        fallback_queries = self._fallback_queries(profile)
        profile_summary = self._build_profile_summary(profile)
        search_count = 0
        scrape_count = 0
        failed_domains: dict[str, int] = {}

        for iteration in range(self.max_iter):
            if len(collected_jobs) >= self.max_jobs:
                break

            pending_url = self._next_unscraped_url(search_results, scraped_urls, failed_domains)
            if not trajectory and fallback_queries and search_count < self.max_searches:
                action = AgentAction(
                    type="search",
                    input={"query": fallback_queries.pop(0)},
                    thought="Start with deterministic seed search for reliable coverage.",
                )
            elif pending_url and scrape_count < self.max_scrapes:
                action = AgentAction(
                    type="scrape",
                    input={"url": pending_url},
                    thought="Scrape queued candidate before asking for more search guidance.",
                )
            else:
                action = await self._think_and_act(
                    profile_summary=profile_summary,
                    trajectory=trajectory,
                    jobs_so_far=len(collected_jobs),
                    fallback_queries=fallback_queries,
                )

            if action.type == "finish":
                pending_url = self._next_unscraped_url(search_results, scraped_urls, failed_domains)
                if pending_url:
                    action = AgentAction(
                        type="scrape",
                        input={"url": pending_url},
                        thought="Scrape pending candidate before finishing.",
                    )
                elif len(collected_jobs) < self.max_jobs and fallback_queries:
                    action = AgentAction(
                        type="search",
                        input={"query": fallback_queries.pop(0)},
                        thought="Use fallback search to improve result coverage before finishing.",
                    )
                else:
                    logger.info("Agent finished after %s iterations with %s jobs.", iteration, len(collected_jobs))
                    break

            if action.type == "search" and search_count >= self.max_searches:
                pending_url = self._next_unscraped_url(search_results, scraped_urls, failed_domains)
                if pending_url and scrape_count < self.max_scrapes:
                    action = AgentAction(
                        type="scrape",
                        input={"url": pending_url},
                        thought="Search cap reached; scrape pending candidate.",
                    )
                else:
                    logger.info("Agent reached search cap with %s jobs.", len(collected_jobs))
                    break

            if action.type == "scrape" and scrape_count >= self.max_scrapes:
                if fallback_queries and search_count < self.max_searches:
                    action = AgentAction(
                        type="search",
                        input={"query": fallback_queries.pop(0)},
                        thought="Scrape cap reached; use remaining search coverage.",
                    )
                else:
                    logger.info("Agent reached scrape cap with %s jobs.", len(collected_jobs))
                    break

            observation = await self._execute_action(
                action=action,
                scraped_urls=scraped_urls,
                search_results=search_results,
                collected_jobs=collected_jobs,
                profile=profile,
                failed_domains=failed_domains,
            )
            if action.type == "search":
                search_count += 1
            elif action.type == "scrape":
                scrape_count += 1

            trajectory.append(
                TrajectoryStep(
                    thought=action.thought,
                    action=action,
                    observation=observation,
                )
            )

            if len(trajectory) >= 6:
                trajectory = self._summarize_trajectory(trajectory)

        return sorted(collected_jobs, key=lambda job: job.relevance_score, reverse=True)

    async def _think_and_act(
        self,
        profile_summary: str,
        trajectory: list[TrajectoryStep],
        jobs_so_far: int,
        fallback_queries: list[str],
    ) -> AgentAction:
        trajectory_text = self._format_trajectory(trajectory)
        prompt = f"""USER PROFILE:
{profile_summary}

JOBS COLLECTED SO FAR: {jobs_so_far}
TARGET: {self.max_jobs} jobs

TRAJECTORY SO FAR:
{trajectory_text}

What is your next action? Respond with JSON only."""

        try:
            response = await self.llm.complete(prompt=prompt, system=REACT_SYSTEM_PROMPT)
            raw = self._parse_json_object(response)
            action_type = str(raw.get("action", "")).lower().strip()
            if action_type not in VALID_ACTIONS:
                raise ValueError(f"Unknown action: {action_type}")
            return AgentAction(
                type=action_type,
                input=raw.get("input") if isinstance(raw.get("input"), dict) else {},
                thought=str(raw.get("thought") or ""),
            )
        except Exception as exc:
            logger.warning("Failed to parse LLM action: %s", exc)
            if fallback_queries:
                return AgentAction(
                    type="search",
                    input={"query": fallback_queries.pop(0)},
                    thought="Fallback search after invalid LLM action.",
                )
            return AgentAction(type="finish", input={}, thought="No valid action available.")

    async def _execute_action(
        self,
        action: AgentAction,
        scraped_urls: set[str],
        search_results: dict[str, SearchResult],
        collected_jobs: list[ScoredJob],
        profile: UserProfile,
        failed_domains: dict[str, int] | None = None,
    ) -> str:
        failed_domains = failed_domains if failed_domains is not None else {}
        if action.type == "search":
            return await self._execute_search(action, search_results)

        if action.type == "scrape":
            return await self._execute_scrape(
                action,
                scraped_urls,
                search_results,
                collected_jobs,
                profile,
                failed_domains,
            )

        if action.type == "score":
            return await self._execute_score(action, collected_jobs, profile)

        return f"Unknown action type: {action.type}"

    async def _execute_search(
        self,
        action: AgentAction,
        search_results: dict[str, SearchResult],
    ) -> str:
        query = str(action.input.get("query") or "").strip()
        if not query:
            return "Search skipped: empty query."

        logger.debug("Searching: %s", query)
        results = await self.searxng.search(query, num_results=settings.REACT_AGENT_SEARCH_RESULTS_PER_QUERY)
        job_results = [result for result in results if result.is_job_listing]
        for result in job_results:
            search_results[normalize_url(result.url)] = SearchResult(
                title=result.title,
                url=normalize_url(result.url),
                snippet=result.snippet,
                source=result.source,
                is_job_listing=result.is_job_listing,
            )

        if not job_results:
            return f"No job listing URLs found for query: {query}"

        lines = [f"Found {len(job_results)} job listing URLs:"]
        lines.extend(f"- [{result.source}] {result.title}: {result.url}" for result in job_results[:10])
        return "\n".join(lines)

    async def _execute_scrape(
        self,
        action: AgentAction,
        scraped_urls: set[str],
        search_results: dict[str, SearchResult],
        collected_jobs: list[ScoredJob],
        profile: UserProfile,
        failed_domains: dict[str, int] | None = None,
    ) -> str:
        failed_domains = failed_domains if failed_domains is not None else {}
        url = normalize_url(str(action.input.get("url") or "").strip())
        if not url:
            url = self._next_unscraped_url(search_results, scraped_urls, failed_domains)
        if not url:
            return "Scrape skipped: no URL provided and no pending search result is available."
        if url in scraped_urls:
            return "Already scraped this URL. Skipping."
        if any(job.source_url == url for job in collected_jobs):
            return "Already collected this URL. Skipping."

        scraped_urls.add(url)
        logger.debug("Scraping: %s", url)
        page: ScrapedPage = await self.scraper.scrape(url, retries=settings.SCRAPLING_RETRIES)
        if not page.success:
            self._record_domain_failure(failed_domains, url)
            return f"Scraping failed: {page.error}"

        if is_aggregate_url(url):
            detail_urls = [
                candidate
                for candidate in extract_job_urls(url, page.html, page.text_content, limit=20)
                if candidate not in scraped_urls and candidate not in search_results
            ]
            for candidate in detail_urls:
                search_results[candidate] = SearchResult(
                    title=f"Candidate from {url}",
                    url=candidate,
                    snippet="Extracted from aggregate job page.",
                    source=self._detect_platform(candidate),
                    is_job_listing=True,
                )
            if detail_urls:
                return f"Aggregate page expanded into {len(detail_urls)} detail job URLs."
            return "Aggregate page skipped: no detail job URLs found."

        extracted = await self.extractor.extract(page.text_content, url)
        if not extracted.is_valid_job:
            self._record_domain_failure(failed_domains, url)
            return "Page is not a valid job listing."

        assessment = assess_job_quality(
            profile,
            extracted,
            url,
            max_age_days=settings.REACT_AGENT_MAX_JOB_AGE_DAYS,
        )
        if not assessment.accepted:
            return f"Quality gate rejected job: {'; '.join(assessment.reasons)}"

        score_data = await self._score_job(extracted.to_dict(), profile)
        score = calibrated_score(score_data["score"], assessment)
        reason = self._combine_reasons(score_data["reason"], assessment.reasons)
        if score >= settings.REACT_AGENT_MIN_RELEVANCE_SCORE:
            collected_jobs.append(
                ScoredJob(
                    extracted=extracted,
                    source_url=url,
                    source_platform=self._detect_platform(url),
                    relevance_score=score,
                    relevance_reason=reason,
                )
            )
            return (
                f"Scraped and scored {score:.2f}. Added job: "
                f"{extracted.title or 'Untitled role'} at {extracted.company or 'Unknown company'}. {reason}"
            )

        return f"Scraped and scored {score:.2f}, below threshold. {reason}"

    async def _execute_score(
        self,
        action: AgentAction,
        collected_jobs: list[ScoredJob],
        profile: UserProfile,
    ) -> str:
        job_data = action.input.get("job_data")
        if not isinstance(job_data, dict):
            return "Score skipped: missing job_data."

        score_data = await self._score_job(job_data, profile)
        extracted = ExtractedJob(
            title=job_data.get("title"),
            company=job_data.get("company"),
            location=job_data.get("location"),
            job_type=job_data.get("job_type"),
            salary_range=job_data.get("salary_range"),
            posted_date_raw=job_data.get("posted_date_raw"),
            posted_at=job_data.get("posted_at"),
            description_clean=job_data.get("description_clean", ""),
            description_short=job_data.get("description_short", ""),
            required_skills=job_data.get("required_skills", []),
            contact_email=job_data.get("contact_email"),
            is_valid_job=job_data.get("is_valid_job", True),
        )
        url = normalize_url(str(action.input.get("url") or job_data.get("source_url") or "").strip())
        if not url:
            return "Score skipped: missing URL for scored job."
        assessment = assess_job_quality(
            profile,
            extracted,
            url,
            max_age_days=settings.REACT_AGENT_MAX_JOB_AGE_DAYS,
        )
        if not assessment.accepted:
            return f"Score skipped by quality gate: {'; '.join(assessment.reasons)}"

        score = calibrated_score(score_data["score"], assessment)
        reason = self._combine_reasons(score_data["reason"], assessment.reasons)
        if score < settings.REACT_AGENT_MIN_RELEVANCE_SCORE:
            return f"Scored {score:.2f}, below threshold. {reason}"
        if any(job.source_url == url for job in collected_jobs):
            return "Score skipped: job already collected."

        collected_jobs.append(
            ScoredJob(
                extracted=extracted,
                source_url=url,
                source_platform=self._detect_platform(url),
                relevance_score=score,
                relevance_reason=reason,
            )
        )
        return f"Scored {score:.2f}. Added to results. {reason}"

    async def _score_job(self, job_data: dict[str, Any], profile: UserProfile) -> dict[str, Any]:
        prompt = f"""Score this job's relevance for the user profile on a scale of 0.0 to 1.0.

USER PROFILE:
- Title: {profile.current_title}
- Experience: {profile.experience_years} years
- Skills: {', '.join(profile.skills)}
- Preferred locations: {', '.join(profile.preferred_locations)}
- Industries: {', '.join(profile.industries)}

JOB:
- Title: {job_data.get('title')}
- Company: {job_data.get('company')}
- Location: {job_data.get('location')}
- Posted at: {job_data.get('posted_at') or job_data.get('posted_date_raw')}
- Required skills: {', '.join(job_data.get('required_skills') or [])}
- Job type: {job_data.get('job_type')}

Only score fresh jobs that are clearly posted within the last {settings.REACT_AGENT_MAX_JOB_AGE_DAYS} days.
Give a Pakistan-location bonus only if the job is in Pakistan or explicitly remote/open to Pakistan/global/APAC candidates.
Penalize roles where required experience or seniority is above the user's profile.
Respond in JSON: {{"score": 0.0, "reason": "1-sentence explanation"}}"""

        try:
            response = await self.llm.complete_json(prompt=prompt)
            score = max(0.0, min(1.0, float(response.get("score", 0.0))))
            reason = str(response.get("reason") or "No reason provided.").strip()
            return {"score": score, "reason": reason}
        except Exception as exc:
            logger.warning("Job scoring failed: %s", exc)
            return {
                "score": self._heuristic_score(job_data, profile),
                "reason": "Heuristic fallback used because LLM scoring was unavailable.",
            }

    def _build_profile_summary(self, profile: UserProfile) -> str:
        education = profile.education or {}
        return f"""Name: {profile.full_name}
Title: {profile.current_title}
Experience: {profile.experience_years} years
Skills: {', '.join(profile.skills)}
Education: {education.get('degree', 'N/A')} in {education.get('field', 'N/A')}
Preferred locations: {', '.join(profile.preferred_locations)}
Industries: {', '.join(profile.industries)}
Job types: {', '.join(profile.preferred_job_types)}
Languages: {', '.join(profile.languages)}"""

    def _format_trajectory(self, trajectory: list[TrajectoryStep]) -> str:
        if not trajectory:
            return "No actions taken yet."
        lines = []
        for index, step in enumerate(trajectory, 1):
            lines.append(f"Step {index}:")
            lines.append(f"  Thought: {step.thought}")
            lines.append(f"  Action: {step.action.type}({step.action.input})")
            lines.append(f"  Observation: {step.observation[:500]}")
        return "\n".join(lines)

    def _summarize_trajectory(self, trajectory: list[TrajectoryStep]) -> list[TrajectoryStep]:
        summary_step = TrajectoryStep(
            thought="Summary of previous actions",
            action=AgentAction(type="summary", input={}),
            observation=f"Earlier steps summarized. Keeping the latest {min(3, len(trajectory))} steps verbatim.",
        )
        return [summary_step] + trajectory[-3:]

    def _fallback_queries(self, profile: UserProfile) -> list[str]:
        title = profile.current_title or "software engineer"
        skills = " ".join((profile.skills or [])[:3])
        locations = profile.preferred_locations or ["Pakistan", "Remote"]
        base = " ".join(part for part in [title, skills] if part).strip()
        location = locations[0] if locations else "Pakistan"
        recency = "posted today OR yesterday OR last 3 days OR new"
        return [
            f'site:mustakbil.com/jobs/job {base} {location} Pakistan {recency}',
            f'site:rozee.pk/job {base} {location} Pakistan {recency}',
            f'site:bayt.com/en/pakistan/jobs {base} {recency}',
            f'site:applytojob.com/apply {base} Pakistan {recency}',
            f'{base} jobs Pakistan -linkedin {recency}',
            f'{base} remote jobs open to Pakistan {recency}',
        ]

    def _next_unscraped_url(
        self,
        search_results: dict[str, SearchResult],
        scraped_urls: set[str],
        failed_domains: dict[str, int] | None = None,
    ) -> str:
        for url in search_results:
            if url in scraped_urls:
                continue
            domain = self._domain(url)
            if failed_domains and failed_domains.get(domain, 0) >= 2:
                continue
            if url not in scraped_urls:
                return url
        return ""

    def _record_domain_failure(self, failed_domains: dict[str, int], url: str) -> None:
        domain = self._domain(url)
        failed_domains[domain] = failed_domains.get(domain, 0) + 1

    def _domain(self, url: str) -> str:
        return urlparse(url).netloc.lower().removeprefix("www.")

    def _combine_reasons(self, llm_reason: str, quality_reasons: list[str]) -> str:
        reason = str(llm_reason or "No reason provided.").strip()
        if quality_reasons:
            return f"{reason} Quality checks: {'; '.join(quality_reasons)}."
        return reason

    def _heuristic_score(self, job_data: dict[str, Any], profile: UserProfile) -> float:
        text = " ".join(
            str(value or "")
            for value in [
                job_data.get("title"),
                job_data.get("company"),
                job_data.get("location"),
                job_data.get("job_type"),
                job_data.get("description_clean"),
                job_data.get("description_short"),
            ]
        ).lower()
        score = 0.25
        for skill in profile.skills or []:
            normalized = str(skill).lower().strip()
            if normalized and normalized in text:
                score += 0.08
        if any(location.lower() in text for location in profile.preferred_locations or []):
            score += 0.15
        if "pakistan" in text or "remote" in text:
            score += 0.1
        if profile.current_title and any(part in text for part in profile.current_title.lower().split()):
            score += 0.1
        return round(max(0.0, min(0.82, score)), 3)

    def _parse_json_object(self, response: str) -> dict[str, Any]:
        text = str(response or "").strip()
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()
        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                text = text[start : end + 1]
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object")
        return data

    def _detect_platform(self, url: str) -> str:
        url_lower = url.lower()
        if "linkedin.com" in url_lower:
            return "linkedin"
        if "indeed.com" in url_lower:
            return "indeed"
        if "glassdoor.com" in url_lower:
            return "glassdoor"
        if "rozee.pk" in url_lower:
            return "rozee"
        if "mustakbil.com" in url_lower:
            return "mustakbil"
        if "bayt.com" in url_lower:
            return "bayt"
        return "direct"
