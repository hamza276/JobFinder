import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.profile import UserProfile
from app.models.user import User

router = APIRouter()


class EducationPayload(BaseModel):
    degree: str = ""
    field: str = ""
    institution: str = ""
    year: str = ""


class ProfileCreateRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    current_title: str = Field(..., min_length=1, max_length=255)
    experience_years: int = Field(default=0, ge=0, le=60)
    skills: list[str] = Field(default_factory=list)
    education: EducationPayload | dict[str, Any] = Field(default_factory=EducationPayload)
    preferred_locations: list[str] = Field(default_factory=list)
    preferred_job_types: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    languages: list[str] = Field(default_factory=lambda: ["English", "Urdu"])
    bio: str | None = None

    @field_validator("skills", "preferred_locations", "preferred_job_types", "industries", "languages", mode="before")
    @classmethod
    def clean_string_list(cls, value):
        return _clean_string_list(value)

    @model_validator(mode="after")
    def validate_salary_range(self):
        _ensure_salary_range(self.salary_min, self.salary_max)
        return self


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    current_title: str | None = Field(default=None, min_length=1, max_length=255)
    experience_years: int | None = Field(default=None, ge=0, le=60)
    skills: list[str] | None = None
    education: EducationPayload | dict[str, Any] | None = None
    preferred_locations: list[str] | None = None
    preferred_job_types: list[str] | None = None
    industries: list[str] | None = None
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    languages: list[str] | None = None
    bio: str | None = None

    @field_validator("skills", "preferred_locations", "preferred_job_types", "industries", "languages", mode="before")
    @classmethod
    def clean_string_list(cls, value):
        return _clean_string_list(value)

    @model_validator(mode="after")
    def validate_salary_range(self):
        _ensure_salary_range(self.salary_min, self.salary_max)
        return self


class ProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    current_title: str
    experience_years: int
    skills: list[str]
    education: dict[str, Any]
    preferred_locations: list[str]
    preferred_job_types: list[str]
    industries: list[str]
    salary_min: int | None
    salary_max: int | None
    languages: list[str]
    bio: str | None
    last_scanned_at: Any = None
    created_at: Any
    updated_at: Any

    model_config = ConfigDict(from_attributes=True)


class ProfileCreateResponse(ProfileResponse):
    profile_id: uuid.UUID


def _normalize_profile_payload(payload: BaseModel) -> dict[str, Any]:
    data = payload.model_dump(exclude_unset=True)
    education = data.get("education")
    if isinstance(education, BaseModel):
        data["education"] = education.model_dump()
    return data


def _clean_string_list(value) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.split(",")
    cleaned = []
    seen = set()
    for item in value:
        text = str(item).strip()
        key = text.lower()
        if text and key not in seen:
            cleaned.append(text)
            seen.add(key)
    return cleaned


def _ensure_salary_range(salary_min: int | None, salary_max: int | None) -> None:
    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        raise ValueError("salary_min cannot be greater than salary_max")


@router.post("", response_model=ProfileCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: ProfileCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ProfileCreateResponse:
    user = User()
    profile_data = _normalize_profile_payload(payload)
    profile = UserProfile(user=user, **profile_data)

    db.add(user)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    return ProfileCreateResponse(
        **ProfileResponse.model_validate(profile).model_dump(),
        profile_id=profile.id,
    )


@router.get("/{user_id}", response_model=ProfileResponse)
async def get_profile(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.patch("/{user_id}", response_model=ProfileResponse)
async def update_profile(
    user_id: uuid.UUID,
    payload: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    data = _normalize_profile_payload(payload)
    for field, value in data.items():
        setattr(profile, field, value)
    try:
        _ensure_salary_range(profile.salary_min, profile.salary_max)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    await db.commit()
    await db.refresh(profile)
    return profile
