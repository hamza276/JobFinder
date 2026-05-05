from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pkjobs"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # SearXNG
    SEARXNG_URL: str = "https://searxngapp.app.digitalsgalaxy.com"

    # Scrapling
    SCRAPLING_API_URL: str = "https://scraplingbackend.app.digitalsgalaxy.com"
    SCRAPLING_FETCH_MODE: str = "auto"  # "auto" | "http" | "dynamic" | "stealth"
    SCRAPLING_HEADLESS: bool = True
    SCRAPLING_TIMEOUT_MS: int = 30000
    SCRAPLING_WAIT_MS: int = 1000
    SCRAPLING_RETRIES: int = 2
    SCRAPLING_SOLVE_CLOUDFLARE: bool = False
    SCRAPLING_PROXY: str = ""

    # LLM
    LLM_PROVIDER: str = "groq"     # "groq" | "anthropic" | "ollama"
    LLM_MODEL: str = ""            # if empty, each provider uses its default

    GROQ_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Agent
    REACT_AGENT_MAX_JOBS: int = 20
    REACT_AGENT_MAX_ITER: int = 40
    REACT_AGENT_MAX_SEARCHES: int = 8
    REACT_AGENT_MAX_SCRAPES: int = 14
    REACT_AGENT_SCAN_TIMEOUT_SECONDS: int = 600
    REACT_AGENT_MIN_RELEVANCE_SCORE: float = 0.55
    REACT_AGENT_MAX_JOB_AGE_DAYS: int = 3
    REACT_AGENT_SEARCH_RESULTS_PER_QUERY: int = 20

    # Rate limiting
    MANUAL_SCAN_COOLDOWN_SECONDS: int = 3600   # 1 hour between manual scans

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
