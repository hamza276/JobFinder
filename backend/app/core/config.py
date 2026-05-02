from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pkjobs"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # SearXNG
    SEARXNG_URL: str = "http://localhost:8888"

    # Scrapling
    SCRAPLING_FETCH_MODE: str = "auto"  # "auto" | "http" | "dynamic" | "stealth"
    SCRAPLING_HEADLESS: bool = True
    SCRAPLING_TIMEOUT_MS: int = 30000
    SCRAPLING_WAIT_MS: int = 1000
    SCRAPLING_SOLVE_CLOUDFLARE: bool = False
    SCRAPLING_PROXY: str = ""

    # LLM
    LLM_PROVIDER: str = "openai"   # "openai" | "anthropic" | "ollama"
    LLM_MODEL: str = ""            # if empty, each provider uses its default

    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Agent
    REACT_AGENT_MAX_JOBS: int = 20
    REACT_AGENT_MAX_ITER: int = 10

    # Rate limiting
    MANUAL_SCAN_COOLDOWN_SECONDS: int = 3600   # 1 hour between manual scans

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
