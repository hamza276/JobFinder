import unittest

from app.services.fetcher.scrapling_client import ScraplingClient
from app.services.fetcher.searxng_client import SearXNGClient


class FetcherClientTests(unittest.TestCase):
    def test_searxng_detects_job_listing_urls(self):
        client = SearXNGClient()

        self.assertTrue(client._is_job_listing("https://rozee.pk/job/frontend", "Frontend job", "Apply now"))
        self.assertTrue(client._is_job_listing("https://example.com/careers/react-engineer", "React Engineer", "Requirements: React"))
        self.assertFalse(client._is_job_listing("https://youtube.com/watch?v=1", "Video", "jobs"))
        self.assertFalse(client._is_job_listing("https://weworkremotely.com/", "Remote jobs", "Remote jobs"))
        self.assertFalse(client._is_job_listing("https://www.linkedin.com/jobs", "Jobs", "Search jobs"))
        self.assertFalse(client._is_job_listing("https://pk.linkedin.com/jobs/view/123", "React job", "Apply now"))
        self.assertFalse(client._is_job_listing("https://www.crossover.com/", "Crossover", "Remote jobs"))

    def test_searxng_extracts_known_sources(self):
        client = SearXNGClient()

        self.assertEqual(client._extract_source("https://www.linkedin.com/jobs/view/1"), "linkedin")
        self.assertEqual(client._extract_source("https://company.example.com/careers/1"), "company")

    def test_scrapling_strategy_selection(self):
        client = ScraplingClient()

        self.assertEqual(client._strategies_for_url("https://linkedin.com/jobs/view/1"), ["stealth", "dynamic", "http"])
        self.assertEqual(client._strategies_for_url("https://company.example.com/careers/1"), ["http", "dynamic"])

    def test_scrapling_text_cleanup_limits_whitespace_and_length(self):
        client = ScraplingClient()

        cleaned = client._clean_text(("hello   world\n" * 1000))

        self.assertNotIn("\n", cleaned)
        self.assertLessEqual(len(cleaned), 8000)

    def test_scrapling_remote_payload_uses_hosted_api_contract(self):
        client = ScraplingClient()

        payload = client._build_payload("https://example.com/job", "http")

        self.assertEqual(client.base_url, "https://scraplingbackend.app.digitalsgalaxy.com")
        self.assertEqual(payload["url"], "https://example.com/job")
        self.assertEqual(payload["extraction_type"], "html")
        self.assertEqual(payload["follow_redirects"], "safe")
        self.assertEqual(payload["retries"], 1)

    def test_scrapling_html_content_is_cleaned_to_text(self):
        client = ScraplingClient()

        text = client._html_to_text("<html><body><nav>Menu</nav><h1>React Job</h1><p>Apply now</p></body></html>")

        self.assertIn("React Job", text)
        self.assertIn("Apply now", text)
        self.assertNotIn("Menu", text)


if __name__ == "__main__":
    unittest.main()
