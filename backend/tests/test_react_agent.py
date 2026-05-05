import json
import unittest

from app.services.fetcher.react_agent import AgentAction, ReActJobAgent
from app.services.fetcher.scrapling_client import ScrapedPage
from app.services.fetcher.searxng_client import SearchResult
from app.services.parser.jd_extractor import ExtractedJob
from tests.helpers import make_profile, run_async


class FakeLLM:
    def __init__(self, actions=None, score=0.82):
        self.actions = list(actions or [])
        self.score = score

    async def complete(self, prompt: str, system: str = "") -> str:
        if self.actions:
            return json.dumps(self.actions.pop(0))
        return json.dumps({"thought": "done", "action": "finish", "input": {}})

    async def complete_json(self, prompt: str, system: str = "", schema: dict | None = None):
        return {"score": self.score, "reason": "Strong skills and location match."}


class InvalidActionLLM(FakeLLM):
    async def complete(self, prompt: str, system: str = "") -> str:
        return "not json"


class FakeSearch:
    def __init__(self):
        self.queries = []

    async def search(self, query: str, num_results: int = 10):
        self.queries.append(query)
        return [
            SearchResult(
                title="React Developer",
                url="https://example.com/jobs/react",
                snippet="Apply now for React role",
                source="direct",
                is_job_listing=True,
            )
        ]


class FakeScraper:
    def __init__(self):
        self.urls = []

    async def scrape(self, url: str, retries: int = 3):
        self.urls.append(url)
        html = '<a href="https://pk.linkedin.com/jobs/view/123">Detail</a>' if "react.js-jobs" in url else "<html></html>"
        return ScrapedPage(url=url, text_content="x" * 200, html=html, success=True)


class FakeExtractor:
    async def extract(self, text: str, url: str):
        return ExtractedJob(
            title="React Developer",
            company="Acme",
            location="Karachi",
            job_type="full-time",
            description_clean="Build React products.",
            description_short="Frontend role.",
            required_skills=["React", "TypeScript"],
            contact_email="jobs@example.com",
            is_valid_job=True,
        )


class ReActAgentTests(unittest.TestCase):
    def make_agent(self, llm):
        return ReActJobAgent(llm=llm, searxng=FakeSearch(), scraper=FakeScraper(), extractor=FakeExtractor())

    def test_run_searches_scrapes_scores_and_collects_job(self):
        llm = FakeLLM(
            actions=[
                {"thought": "search", "action": "search", "input": {"query": "react jobs karachi"}},
                {"thought": "scrape", "action": "scrape", "input": {"url": "https://example.com/jobs/react"}},
                {"thought": "finish", "action": "finish", "input": {}},
            ]
        )
        agent = self.make_agent(llm)

        jobs = run_async(agent.run(make_profile()))

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].source_url, "https://example.com/jobs/react")
        self.assertEqual(jobs[0].relevance_score, 0.82)

    def test_scrape_without_url_uses_pending_search_result(self):
        llm = FakeLLM(
            actions=[
                {"thought": "search", "action": "search", "input": {"query": "react jobs"}},
                {"thought": "scrape first", "action": "scrape", "input": {}},
                {"thought": "finish", "action": "finish", "input": {}},
            ]
        )
        agent = self.make_agent(llm)

        jobs = run_async(agent.run(make_profile()))

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].source_platform, "direct")

    def test_low_scored_job_is_not_collected(self):
        llm = FakeLLM(
            actions=[
                {"thought": "search", "action": "search", "input": {"query": "react jobs"}},
                {"thought": "scrape first", "action": "scrape", "input": {}},
            ],
            score=0.2,
        )
        agent = self.make_agent(llm)

        jobs = run_async(agent.run(make_profile()))

        self.assertEqual(jobs, [])

    def test_invalid_llm_action_falls_back_to_seed_search(self):
        search = FakeSearch()
        agent = ReActJobAgent(llm=InvalidActionLLM(), searxng=search, scraper=FakeScraper(), extractor=FakeExtractor())

        jobs = run_async(agent.run(make_profile()))

        self.assertEqual(len(jobs), 1)
        self.assertTrue(search.queries)

    def test_execute_score_action_adds_manual_job_data(self):
        agent = self.make_agent(FakeLLM(score=0.7))
        collected = []

        observation = run_async(
            agent._execute_action(
                AgentAction(
                    type="score",
                    input={
                        "url": "https://example.com/jobs/manual",
                        "job_data": {
                            "title": "React Frontend Engineer",
                            "company": "Acme",
                            "location": "Remote",
                            "description_clean": "Build React interfaces",
                            "description_short": "Backend role",
                            "required_skills": ["React"],
                        },
                    },
                ),
                scraped_urls=set(),
                search_results={},
                collected_jobs=collected,
                profile=make_profile(),
            )
        )

        self.assertIn("Added", observation)
        self.assertEqual(len(collected), 1)

    def test_aggregate_page_expands_detail_urls_without_saving_aggregate(self):
        agent = self.make_agent(FakeLLM(score=0.8))
        search_results = {
            "https://pk.linkedin.com/jobs/react.js-jobs": SearchResult(
                title="React jobs",
                url="https://pk.linkedin.com/jobs/react.js-jobs",
                snippet="React jobs in Pakistan",
                source="linkedin",
                is_job_listing=True,
            )
        }

        observation = run_async(
            agent._execute_action(
                AgentAction(type="scrape", input={"url": "https://pk.linkedin.com/jobs/react.js-jobs"}),
                scraped_urls=set(),
                search_results=search_results,
                collected_jobs=[],
                profile=make_profile(),
            )
        )

        self.assertIn("expanded", observation)
        self.assertIn("https://pk.linkedin.com/jobs/view/123", search_results)

    def test_heuristic_score_used_when_llm_score_fails(self):
        class BrokenScoreLLM(FakeLLM):
            async def complete_json(self, prompt: str, system: str = "", schema: dict | None = None):
                raise RuntimeError("rate limited")

        agent = self.make_agent(BrokenScoreLLM())

        score = run_async(
            agent._score_job(
                {
                    "title": "React Frontend Engineer",
                    "company": "Acme",
                    "location": "Pakistan Remote",
                    "description_clean": "React TypeScript Next.js role",
                    "required_skills": ["React", "TypeScript"],
                },
                make_profile(),
            )
        )

        self.assertGreaterEqual(score["score"], 0.5)
        self.assertIn("Heuristic", score["reason"])


if __name__ == "__main__":
    unittest.main()
