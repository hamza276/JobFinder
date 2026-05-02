"""
ReAct Agent — Core job discovery intelligence.

Pattern: Thought → Action → Observation → loop
The LLM drives all decisions. We just execute what it decides.
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.models.profile import UserProfile
from app.services.llm.base import BaseLLMProvider
from app.services.fetcher.searxng_client import SearXNGClient, SearchResult
from app.services.fetcher.scrapling_client import ScraplingClient, ScrapedPage
from app.services.parser.jd_extractor import JDExtractor, ExtractedJob
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AgentAction:
    type: str          # "search" | "scrape" | "score" | "finish"
    input: dict        # varies by type
    thought: str = ""  # LLM's reasoning before this action


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
Your goal: find relevant job listings for the user based on their profile.

You have access to these actions:
1. search(query: str) — search for job listings using SearXNG
2. scrape(url: str) — scrape full job details from a URL
3. score(job_data: dict) — evaluate how relevant a job is for this user (score 0.0-1.0)
4. finish() — stop when you have enough jobs (15-20 good matches)

Rules:
- Generate diverse, targeted search queries (mix platforms: linkedin, indeed, rozee.pk, mustakbil)
- Only scrape URLs that look like actual job listings
- Score honestly — a low score is better than a misleading high score
- Prioritize Pakistan-based jobs + remote roles open to Pakistanis
- If a page is a login wall or 404, mark score as 0 and move on
- Think step by step. Show your reasoning in the "thought" field.

Always respond in JSON:
{
  "thought": "your reasoning here",
  "action": "search|scrape|score|finish",
  "input": { ... }  // action-specific params
}
"""


class ReActJobAgent:
    """
    Full ReAct agent that discovers, scrapes, and scores jobs for a user.
    Called once per user per daily scan.
    """

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

    async def run(self, profile: UserProfile) -> list[ScoredJob]:
        """
        Main entry point. Runs the full ReAct loop for a user.
        Returns a list of scored jobs (sorted by relevance_score desc).
        """
        logger.info(f"Starting ReAct agent for user {profile.user_id}")
        trajectory: list[TrajectoryStep] = []
        collected_jobs: list[ScoredJob] = []
        scraped_urls: set[str] = set()

        profile_summary = self._build_profile_summary(profile)

        for iteration in range(self.max_iter):
            logger.debug(f"Iteration {iteration + 1}/{self.max_iter}")

            # Get next action from LLM
            action = await self._think_and_act(profile_summary, trajectory, len(collected_jobs))

            if action.type == "finish":
                logger.info(f"Agent finished. Collected {len(collected_jobs)} jobs.")
                break

            # Execute action
            observation = await self._execute_action(
                action, scraped_urls, collected_jobs, profile
            )

            # Record trajectory
            trajectory.append(TrajectoryStep(
                thought=action.thought,
                action=action,
                observation=observation,
            ))

            # Summarize trajectory if getting long (context window management)
            if len(trajectory) >= 6:
                trajectory = self._summarize_trajectory(trajectory)

        return sorted(collected_jobs, key=lambda j: j.relevance_score, reverse=True)

    async def _think_and_act(
        self,
        profile_summary: str,
        trajectory: list[TrajectoryStep],
        jobs_so_far: int,
    ) -> AgentAction:
        """Ask the LLM for the next action."""
        trajectory_text = self._format_trajectory(trajectory)
        prompt = f"""USER PROFILE:
{profile_summary}

JOBS COLLECTED SO FAR: {jobs_so_far}
TARGET: {self.max_jobs} jobs

TRAJECTORY SO FAR:
{trajectory_text}

What is your next action? Respond in JSON format as described in the system prompt."""

        response = await self.llm.complete(prompt=prompt, system=REACT_SYSTEM_PROMPT)

        # Parse JSON response
        try:
            raw = json.loads(response.strip())
            return AgentAction(
                type=raw["action"],
                input=raw.get("input", {}),
                thought=raw.get("thought", ""),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse LLM action: {e}. Response: {response[:200]}")
            # Fallback: finish to avoid infinite loop
            return AgentAction(type="finish", input={}, thought="Failed to parse response")

    async def _execute_action(
        self,
        action: AgentAction,
        scraped_urls: set[str],
        collected_jobs: list[ScoredJob],
        profile: UserProfile,
    ) -> str:
        """Execute the chosen action. Returns observation string."""

        if action.type == "search":
            query = action.input.get("query", "")
            logger.debug(f"Searching: {query}")
            results: list[SearchResult] = await self.searxng.search(query, num_results=10)
            job_results = [r for r in results if r.is_job_listing]
            obs = f"Found {len(job_results)} job listing URLs:\n"
            obs += "\n".join([f"- [{r.source}] {r.title}: {r.url}" for r in job_results[:10]])
            return obs

        elif action.type == "scrape":
            url = action.input.get("url", "")
            if url in scraped_urls:
                return f"Already scraped this URL. Skipping."
            scraped_urls.add(url)
            logger.debug(f"Scraping: {url}")
            page: ScrapedPage = await self.scraper.scrape(url)
            if not page.success:
                return f"Scraping failed: {page.error}"
            # Extract job info
            job: ExtractedJob = await self.extractor.extract(page.text_content, url)
            if not job.is_valid_job:
                return "Page is not a valid job listing (login wall, 404, or expired)."
            obs = f"Scraped successfully. Job: {job.title} at {job.company}\n"
            obs += f"Location: {job.location} | Type: {job.job_type} | Posted: {job.posted_date_raw}\n"
            obs += f"Skills required: {', '.join(job.required_skills[:8])}\n"
            obs += f"Contact email found: {'Yes - ' + job.contact_email if job.contact_email else 'No'}"
            return obs

        elif action.type == "score":
            job_data = action.input.get("job_data", {})
            url = action.input.get("url", "")
            score_data = await self._score_job(job_data, profile)
            score = score_data.get("score", 0.0)
            reason = score_data.get("reason", "")

            if score >= 0.35:
                # Reconstruct ExtractedJob from job_data dict
                extracted = ExtractedJob(**{k: v for k, v in job_data.items() if hasattr(ExtractedJob, k)})
                platform = self._detect_platform(url)
                scored_job = ScoredJob(
                    extracted=extracted,
                    source_url=url,
                    source_platform=platform,
                    relevance_score=score,
                    relevance_reason=reason,
                )
                collected_jobs.append(scored_job)
                return f"Scored: {score:.2f}. Reason: {reason}. Added to results."
            else:
                return f"Scored: {score:.2f} (below threshold). Reason: {reason}. Skipped."

        return f"Unknown action type: {action.type}"

    async def _score_job(self, job_data: dict, profile: UserProfile) -> dict:
        """Use LLM to score job relevance against user profile."""
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
- Required skills: {', '.join(job_data.get('required_skills', []))}
- Job type: {job_data.get('job_type')}

Give a Pakistan-location bonus (+0.15) if job is in Pakistan or is remote.
Respond in JSON: {{"score": 0.0-1.0, "reason": "1-sentence explanation"}}"""

        response = await self.llm.complete_json(prompt=prompt)
        return response

    def _build_profile_summary(self, profile: UserProfile) -> str:
        return f"""Name: {profile.full_name}
Title: {profile.current_title}
Experience: {profile.experience_years} years
Skills: {', '.join(profile.skills)}
Education: {profile.education.get('degree', 'N/A')} in {profile.education.get('field', 'N/A')}
Preferred locations: {', '.join(profile.preferred_locations)}
Industries: {', '.join(profile.industries)}
Job types: {', '.join(profile.preferred_job_types)}
Languages: {', '.join(profile.languages)}"""

    def _format_trajectory(self, trajectory: list[TrajectoryStep]) -> str:
        if not trajectory:
            return "No actions taken yet. This is the first step."
        lines = []
        for i, step in enumerate(trajectory, 1):
            lines.append(f"Step {i}:")
            lines.append(f"  Thought: {step.thought}")
            lines.append(f"  Action: {step.action.type}({step.action.input})")
            lines.append(f"  Observation: {step.observation[:200]}...")
        return "\n".join(lines)

    def _summarize_trajectory(self, trajectory: list[TrajectoryStep]) -> list[TrajectoryStep]:
        """Keep last 3 steps and add a summary step at the start."""
        summary_text = f"[Summary of {len(trajectory) - 3} earlier steps: searched for jobs, scraped multiple listings, found some matches]"
        summary_step = TrajectoryStep(
            thought="Summary of previous actions",
            action=AgentAction(type="summary", input={}),
            observation=summary_text,
        )
        return [summary_step] + trajectory[-3:]

    def _detect_platform(self, url: str) -> str:
        url_lower = url.lower()
        if "linkedin.com" in url_lower: return "linkedin"
        if "indeed.com" in url_lower: return "indeed"
        if "glassdoor.com" in url_lower: return "glassdoor"
        if "rozee.pk" in url_lower: return "rozee"
        if "mustakbil.com" in url_lower: return "mustakbil"
        if "bayt.com" in url_lower: return "bayt"
        return "direct"
