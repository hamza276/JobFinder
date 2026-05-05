import unittest
from datetime import datetime

from app.services.parser.jd_extractor import JDExtractor
from tests.helpers import run_async


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    async def complete_json(self, prompt: str, system: str = "", schema: dict | None = None):
        self.calls += 1
        return self.payload


class FailingLLM:
    async def complete_json(self, prompt: str, system: str = "", schema: dict | None = None):
        raise RuntimeError("rate limited")


class JDExtractorTests(unittest.TestCase):
    def test_extracts_valid_job_and_parses_relative_date(self):
        llm = FakeLLM(
            {
                "title": "React Developer",
                "company": "Acme",
                "location": "Karachi",
                "job_type": "full-time",
                "salary_range": "PKR 300k-450k",
                "posted_date_raw": "2 days ago",
                "description_clean": "Build React products.",
                "description_short": "Frontend role.",
                "required_skills": [" React ", "react", "TypeScript"],
                "contact_email": "jobs@example.com",
                "is_valid_job": True,
            }
        )

        job = run_async(JDExtractor(llm).extract("x" * 200, "https://example.com/job/1"))

        self.assertTrue(job.is_valid_job)
        self.assertEqual(job.required_skills, ["React", "TypeScript"])
        self.assertEqual(job.contact_email, "jobs@example.com")
        self.assertIsInstance(job.posted_at, datetime)

    def test_rejects_short_pages_without_llm_call(self):
        llm = FakeLLM({})

        job = run_async(JDExtractor(llm).extract("too short", "https://example.com/job/1"))

        self.assertFalse(job.is_valid_job)
        self.assertEqual(llm.calls, 0)

    def test_invalid_email_is_discarded(self):
        llm = FakeLLM(
            {
                "title": "Engineer",
                "company": "Acme",
                "description_clean": "Role",
                "description_short": "Role",
                "required_skills": "Python, SQL",
                "contact_email": "not-an-email",
                "is_valid_job": True,
            }
        )

        job = run_async(JDExtractor(llm).extract("x" * 200, "https://example.com/job/1"))

        self.assertIsNone(job.contact_email)
        self.assertEqual(job.required_skills, ["Python", "SQL"])

    def test_list_response_uses_first_object(self):
        llm = FakeLLM(
            [
                {
                    "title": "Frontend Engineer",
                    "company": "Acme",
                    "location": "Karachi",
                    "description_clean": "Role",
                    "description_short": "Role",
                    "required_skills": ["React"],
                    "is_valid_job": True,
                }
            ]
        )

        job = run_async(JDExtractor(llm).extract("x" * 200, "https://example.com/job/1"))

        self.assertEqual(job.title, "Frontend Engineer")

    def test_fallback_extracts_conservative_job_when_llm_fails(self):
        text = (
            "Acme Careers is hiring a Senior Frontend Engineer. "
            "This is a full-time remote Pakistan role posted 2 days ago. "
            "Requirements include React, TypeScript, Next.js, Tailwind CSS, REST APIs, and Git. "
            "Apply at jobs@acme.example."
        )

        job = run_async(
            JDExtractor(FailingLLM()).extract(
                text,
                "https://www.linkedin.com/jobs/view/senior-frontend-engineer-at-acme-1234567890",
            )
        )

        self.assertTrue(job.is_valid_job)
        self.assertEqual(job.title, "Senior Frontend Engineer")
        self.assertEqual(job.company, "Acme")
        self.assertEqual(job.location, "Remote, Pakistan")
        self.assertIn("React", job.required_skills)
        self.assertEqual(job.contact_email, "jobs@acme.example")
        self.assertIsInstance(job.posted_at, datetime)

    def test_fallback_rejects_login_wall_when_llm_fails(self):
        text = "Sign in to view this job. Create an account to view more jobs and alerts."

        job = run_async(
            JDExtractor(FailingLLM()).extract(
                text * 5,
                "https://www.linkedin.com/jobs/view/frontend-engineer-at-acme-1234567890",
            )
        )

        self.assertFalse(job.is_valid_job)

    def test_to_dict_serializes_posted_at(self):
        llm = FakeLLM(
            {
                "title": "Engineer",
                "company": "Acme",
                "posted_date_raw": "yesterday",
                "description_clean": "Role",
                "description_short": "Role",
                "required_skills": [],
                "is_valid_job": True,
            }
        )

        job = run_async(JDExtractor(llm).extract("x" * 200, "https://example.com/job/1"))
        data = job.to_dict()

        self.assertIsInstance(data["posted_at"], str)


if __name__ == "__main__":
    unittest.main()
