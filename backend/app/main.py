from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import init_db
from app.api.routes import profile, jobs, email


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await init_db()
    yield


app = FastAPI(
    title="PKJobs API",
    description="AI-powered job discovery for Pakistan",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(email.router, prefix="/api/email", tags=["email"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "pkjobs-api"}
