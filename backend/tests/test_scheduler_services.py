import unittest
import uuid
import asyncio
from unittest.mock import patch

from app.models.profile import UserProfile
from app.models.scan_log import ScanLog
from app.models.job import Job
from app.models.email_draft import EmailDraft
from app.services.fetcher.react_agent import ReActJobAgent, ScoredJob
from app.services.parser.jd_extractor import ExtractedJob
from app.services.scheduler.daily_runner import generate_emails_for_new_jobs, run_scan_for_user, save_jobs_to_db
from tests.helpers import make_profile, run_async


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, execute_values=None):
        self.execute_values = list(execute_values or [])
        self.added = []
        self.commit_count = 0
        self.rollback_count = 0

    async def execute(self, statement):
        if self.execute_values:
            return ScalarResult(self.execute_values.pop(0))
        return ScalarResult(None)

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.commit_count += 1

    async def rollback(self):
        self.rollback_count += 1


class FakeLLM:
    async def complete_json(self, prompt: str, system: str = "", schema: dict | None = None):
        return {"subject": "Application", "body": "Dear team,\n\nI am a strong fit."}


def make_scored_job(url="https://example.com/jobs/1", email="jobs@example.com"):
    return ScoredJob(
        extracted=ExtractedJob(
            title="React Developer",
            company="Acme",
            location="Karachi",
            job_type="full-time",
            description_clean="Build products.",
            description_short="Frontend role.",
            contact_email=email,
            required_skills=["React"],
        ),
        source_url=url,
        source_platform="direct",
        relevance_score=0.9,
        relevance_reason="Strong match.",
    )


def make_job(**overrides):
    data = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "source_url": "https://example.com/jobs/1",
        "source_platform": "direct",
        "title": "React Developer",
        "company": "Acme",
        "location": "Karachi",
        "job_type": "full-time",
        "description_raw": "Build products.",
        "description_short": "Frontend role.",
        "contact_email": "jobs@example.com",
        "relevance_score": 0.9,
    }
    data.update(overrides)
    return Job(**data)


class SchedulerServiceTests(unittest.TestCase):
    def test_save_jobs_persists_new_jobs(self):
        user_id = uuid.uuid4()
        session = FakeSession([None])

        result = run_async(save_jobs_to_db([make_scored_job()], str(user_id), session))

        self.assertEqual(result.new_count, 1)
        self.assertEqual(result.skipped_count, 0)
        self.assertIsInstance(session.added[0], Job)
        self.assertEqual(session.commit_count, 1)

    def test_save_jobs_skips_duplicate_source_url(self):
        user_id = uuid.uuid4()
        session = FakeSession([uuid.uuid4()])

        result = run_async(save_jobs_to_db([make_scored_job()], str(user_id), session))

        self.assertEqual(result.new_count, 0)
        self.assertEqual(result.skipped_count, 1)
        self.assertEqual(session.added, [])

    def test_generate_emails_adds_missing_draft(self):
        user_id = uuid.uuid4()
        job = make_job(user_id=user_id)
        profile = make_profile(user_id=user_id)
        session = FakeSession([None])

        with patch("app.services.scheduler.daily_runner.get_llm_provider", return_value=FakeLLM()):
            run_async(generate_emails_for_new_jobs([job], profile, str(user_id), session))

        self.assertEqual(len(session.added), 1)
        self.assertIsInstance(session.added[0], EmailDraft)
        self.assertEqual(session.added[0].job_id, job.id)

    def test_generate_emails_skips_existing_draft(self):
        user_id = uuid.uuid4()
        job = make_job(user_id=user_id)
        profile = make_profile(user_id=user_id)
        session = FakeSession([uuid.uuid4()])

        with patch("app.services.scheduler.daily_runner.get_llm_provider", return_value=FakeLLM()):
            run_async(generate_emails_for_new_jobs([job], profile, str(user_id), session))

        self.assertEqual(session.added, [])
        self.assertEqual(session.commit_count, 1)

    def test_run_scan_timeout_records_partial_scan_log(self):
        user_id = uuid.uuid4()
        profile = make_profile(user_id=user_id)
        session = FakeSession([profile])

        async def slow_run(self, profile):
            await asyncio.sleep(0.05)
            return []

        with patch("app.services.scheduler.daily_runner.get_llm_provider", return_value=FakeLLM()):
            with patch.object(ReActJobAgent, "run", slow_run):
                with patch("app.services.scheduler.daily_runner.settings.REACT_AGENT_SCAN_TIMEOUT_SECONDS", 0.001):
                    result = run_async(run_scan_for_user(str(user_id), session))

        self.assertEqual(result.status, "partial")
        self.assertIn("timed out", result.errors[0])
        self.assertTrue(any(isinstance(item, ScanLog) for item in session.added))


if __name__ == "__main__":
    unittest.main()
