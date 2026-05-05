import asyncio
import uuid

from app.models.profile import UserProfile


def run_async(coro):
    return asyncio.run(coro)


def make_profile(**overrides):
    data = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "full_name": "Ayesha Khan",
        "current_title": "Frontend Engineer",
        "experience_years": 4,
        "skills": ["React", "TypeScript", "Python"],
        "education": {"degree": "BS", "field": "Computer Science"},
        "preferred_locations": ["Karachi", "Remote"],
        "preferred_job_types": ["full-time", "remote"],
        "industries": ["SaaS", "FinTech"],
        "salary_min": 250000,
        "salary_max": 500000,
        "languages": ["English", "Urdu"],
        "bio": "Builds web apps.",
    }
    data.update(overrides)
    return UserProfile(**data)
