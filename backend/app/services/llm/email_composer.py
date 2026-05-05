import logging
from dataclasses import dataclass
from datetime import datetime

from app.services.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

EMAIL_SYSTEM = """You are a professional career coach helping Pakistani professionals write compelling job application emails.
Write concise, professional, and personalized emails. No fluff. No generic phrases.
Respond ONLY with valid JSON."""

EMAIL_PROMPT = """Write a job application email for this person applying to this job.

APPLICANT PROFILE:
- Name: {full_name}
- Current Title: {current_title}
- Experience: {experience_years} years
- Key Skills: {skills}
- Education: {education}

JOB:
- Title: {job_title}
- Company: {company}
- Location: {location}
- Job Description Summary: {jd_summary}

INSTRUCTIONS:
- 3 paragraphs max: (1) hook/intro, (2) why them + skills match, (3) call to action
- Professional but not robotic
- Reference 2-3 specific skills that match the JD
- Total email body: 150-200 words max
- Subject line should be specific, not generic

Respond in JSON:
{{
  "subject": "email subject line",
  "body": "full email body",
  "to": "{contact_email}"
}}"""


@dataclass
class ComposedEmail:
    to: str | None
    subject: str
    body: str
    generated_at: datetime


class EmailComposer:
    def __init__(self, llm: BaseLLMProvider):
        self.llm = llm

    async def compose(
        self,
        profile,        # UserProfile model
        job,            # Job model
        contact_email: str | None = None,
    ) -> ComposedEmail:
        prompt = EMAIL_PROMPT.format(
            full_name=profile.full_name,
            current_title=profile.current_title,
            experience_years=profile.experience_years,
            skills=", ".join(profile.skills[:8]),
            education=f"{profile.education.get('degree', '')} in {profile.education.get('field', '')}",
            job_title=job.title or "the role",
            company=job.company or "your company",
            location=job.location or "N/A",
            jd_summary=job.description_short or job.description_clean[:300],
            contact_email=contact_email or "to be found",
        )

        try:
            data = await self.llm.complete_json(prompt=prompt, system=EMAIL_SYSTEM)
            subject = str(data.get("subject") or "").strip()
            body = str(data.get("body") or "").strip()
            if not subject or not body:
                raise ValueError("LLM returned an incomplete email draft")
            return ComposedEmail(
                to=contact_email,
                subject=subject,
                body=body,
                generated_at=datetime.utcnow(),
            )
        except Exception as e:
            logger.error(f"Email composition failed for job {job.id}: {e}")
            return ComposedEmail(
                to=contact_email,
                subject=f"Application for {job.title or 'the role'} at {job.company or 'your company'}",
                body="Dear Hiring Manager,\n\nI am interested in this position and believe my skills make me a strong candidate.\n\nPlease find my details attached.\n\nBest regards,\n" + profile.full_name,
                generated_at=datetime.utcnow(),
            )
