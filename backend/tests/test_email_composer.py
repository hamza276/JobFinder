import unittest
import uuid

from app.models.job import Job
from app.services.llm.email_composer import EmailComposer
from tests.helpers import make_profile, run_async


class FakeLLM:
    def __init__(self, payload=None, exc=None):
        self.payload = payload or {}
        self.exc = exc

    async def complete_json(self, prompt: str, system: str = "", schema: dict | None = None):
        if self.exc:
            raise self.exc
        return self.payload


def make_job(**overrides):
    data = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "source_url": "https://example.com/jobs/1",
        "source_platform": "direct",
        "title": "Frontend Engineer",
        "company": "Acme",
        "location": "Remote",
        "job_type": "full-time",
        "description_raw": "Build products.",
        "description_short": "Build React products.",
        "contact_email": "jobs@example.com",
        "relevance_score": 0.9,
    }
    data.update(overrides)
    return Job(**data)


class EmailComposerTests(unittest.TestCase):
    def test_composes_email_from_llm_json(self):
        composer = EmailComposer(FakeLLM({"subject": "React role", "body": "Dear team,\n\nI fit this role."}))

        email = run_async(composer.compose(make_profile(), make_job(), "jobs@example.com"))

        self.assertEqual(email.to, "jobs@example.com")
        self.assertEqual(email.subject, "React role")
        self.assertIn("fit this role", email.body)

    def test_falls_back_when_llm_fails(self):
        composer = EmailComposer(FakeLLM(exc=RuntimeError("boom")))

        email = run_async(composer.compose(make_profile(full_name="Ayesha Khan"), make_job(), None))

        self.assertIn("Application for Frontend Engineer", email.subject)
        self.assertIn("Ayesha Khan", email.body)

    def test_falls_back_when_llm_returns_empty_body(self):
        composer = EmailComposer(FakeLLM({"subject": "Hello", "body": ""}))

        email = run_async(composer.compose(make_profile(), make_job(), "jobs@example.com"))

        self.assertIn("Application for", email.subject)
        self.assertTrue(email.body)


if __name__ == "__main__":
    unittest.main()
