import unittest

from pydantic import ValidationError

from app.api.routes.profile import ProfileCreateRequest, ProfileUpdateRequest


class ProfileSchemaTests(unittest.TestCase):
    def test_create_profile_cleans_string_lists(self):
        payload = ProfileCreateRequest(
            full_name="Ayesha Khan",
            current_title="Frontend Engineer",
            skills=[" React ", "react", "Python", ""],
            preferred_locations="Karachi, Remote, karachi",
            languages="English, Urdu",
        )

        self.assertEqual(payload.skills, ["React", "Python"])
        self.assertEqual(payload.preferred_locations, ["Karachi", "Remote"])
        self.assertEqual(payload.languages, ["English", "Urdu"])

    def test_create_profile_rejects_bad_salary_range(self):
        with self.assertRaises(ValidationError):
            ProfileCreateRequest(
                full_name="Ayesha Khan",
                current_title="Frontend Engineer",
                salary_min=500000,
                salary_max=250000,
            )

    def test_update_profile_allows_partial_payload(self):
        payload = ProfileUpdateRequest(skills=["Python", "python", "SQL"])

        self.assertEqual(payload.skills, ["Python", "SQL"])
        self.assertIsNone(payload.salary_min)

    def test_update_profile_rejects_bad_salary_range_when_both_present(self):
        with self.assertRaises(ValidationError):
            ProfileUpdateRequest(salary_min=900000, salary_max=300000)


if __name__ == "__main__":
    unittest.main()
