import unittest
from datetime import datetime, timedelta

from app.services.fetcher.quality import (
    assess_job_quality,
    calibrated_score,
    extract_job_urls,
    is_aggregate_url,
    is_detail_job_url,
    normalize_url,
)
from app.services.parser.jd_extractor import ExtractedJob
from tests.helpers import make_profile


class QualityTests(unittest.TestCase):
    def test_normalize_url_removes_tracking(self):
        url = normalize_url("HTTPS://PK.LinkedIn.com/jobs/view/123/?utm_source=x&trk=abc&currentJobId=123")

        self.assertEqual(url, "https://pk.linkedin.com/jobs/view/123?currentJobId=123")

    def test_detail_and_aggregate_url_detection(self):
        self.assertTrue(is_detail_job_url("https://pk.linkedin.com/jobs/view/123"))
        self.assertFalse(is_detail_job_url("https://pk.linkedin.com/jobs/react.js-jobs"))
        self.assertTrue(is_aggregate_url("https://pk.linkedin.com/jobs/react.js-jobs"))
        self.assertTrue(is_aggregate_url("https://www.rozee.pk/job/jsearch/q/react"))

    def test_extracts_detail_urls_from_linkedin_aggregate_html(self):
        urls = extract_job_urls(
            "https://pk.linkedin.com/jobs/react.js-jobs",
            '<a href="https://pk.linkedin.com/jobs/view/sr-frontend-engineer-at-company-4366717694?trk=x">Job</a>',
        )

        self.assertEqual(urls, ["https://pk.linkedin.com/jobs/view/sr-frontend-engineer-at-company-4366717694"])

    def test_rejects_foreign_remote_role_not_open_to_pakistan(self):
        assessment = assess_job_quality(
            make_profile(),
            ExtractedJob(
                title="Senior Fullstack Engineer",
                company="Bonapolia",
                location="Poland - Remote",
                description_clean="Build AI systems for a consulting firm.",
                description_short="Remote role.",
                required_skills=["React", "Python"],
                is_valid_job=True,
            ),
            "https://example.com/jobs/123",
        )

        self.assertFalse(assessment.accepted)
        self.assertIn("location", " ".join(assessment.reasons))

    def test_caps_stale_postings(self):
        assessment = assess_job_quality(
            make_profile(),
            ExtractedJob(
                title="Frontend Engineer",
                company="Acme",
                location="Karachi",
                posted_at=datetime.utcnow() - timedelta(days=120),
                description_clean="React TypeScript role.",
                required_skills=["React", "TypeScript"],
                is_valid_job=True,
            ),
            "https://example.com/jobs/123",
        )

        self.assertFalse(assessment.accepted)
        self.assertIn("older", " ".join(assessment.reasons))

    def test_caps_seniority_mismatch(self):
        assessment = assess_job_quality(
            make_profile(experience_years=2),
            ExtractedJob(
                title="Principal Frontend Engineer",
                company="Acme",
                location="Karachi",
                description_clean="Principal frontend role requiring React and TypeScript.",
                required_skills=["React", "TypeScript"],
                is_valid_job=True,
            ),
            "https://example.com/jobs/123",
        )

        self.assertTrue(assessment.accepted)
        self.assertLessEqual(assessment.score_cap, 0.45)

    def test_caps_fullstack_role_for_frontend_profile(self):
        assessment = assess_job_quality(
            make_profile(experience_years=4),
            ExtractedJob(
                title="Senior Full Stack Developer",
                company="Acme",
                location="Pakistan",
                description_clean="Build React and Next.js applications with backend APIs.",
                required_skills=["React", "Next.js"],
                is_valid_job=True,
            ),
            "https://example.com/jobs/123",
        )

        self.assertTrue(assessment.accepted)
        self.assertLessEqual(assessment.score_cap, 0.78)

    def test_caps_part_time_role_for_full_time_profile(self):
        assessment = assess_job_quality(
            make_profile(preferred_job_types=["full-time", "remote"]),
            ExtractedJob(
                title="Part-time Frontend Developer",
                company="Acme",
                location="Pakistan",
                job_type="part-time",
                description_clean="Part-time React role.",
                required_skills=["React"],
                is_valid_job=True,
            ),
            "https://example.com/jobs/123",
        )

        self.assertTrue(assessment.accepted)
        self.assertLessEqual(assessment.score_cap, 0.55)

    def test_calibrated_score_applies_cap_and_multiplier(self):
        assessment = assess_job_quality(
            make_profile(experience_years=2),
            ExtractedJob(
                title="Principal Frontend Engineer",
                company="Acme",
                location="Karachi",
                description_clean="Principal frontend role requiring React and TypeScript.",
                required_skills=["React", "TypeScript"],
                is_valid_job=True,
            ),
            "https://example.com/jobs/123",
        )

        self.assertLessEqual(calibrated_score(0.95, assessment), 0.45)


if __name__ == "__main__":
    unittest.main()
