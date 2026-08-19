import os
import logging
from pathlib import Path

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import chat, media, memories, jobs, matcher, ats, authenticity, insights, outreach

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="malloc()",
    description="Voice-enabled personal AI assistant with long-term memory backend API and web interface",
    version="0.1.0-stage1",
)

# Enable CORS for cross-domain access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Stage 1: create tables directly. Alembic migrations arrive once the
# schema stabilizes (Stage 4+, alongside the memory tables).
Base.metadata.create_all(bind=engine)

app.include_router(chat.router)
app.include_router(chat.router, prefix="/api")
app.include_router(media.router)
app.include_router(media.router, prefix="/api")
app.include_router(memories.router)
app.include_router(memories.router, prefix="/api")
app.include_router(jobs.router)
app.include_router(jobs.router, prefix="/api")
app.include_router(matcher.router)
app.include_router(matcher.router, prefix="/api")
app.include_router(ats.router)
app.include_router(ats.router, prefix="/api")
app.include_router(authenticity.router)
app.include_router(authenticity.router, prefix="/api")
app.include_router(insights.router)
app.include_router(insights.router, prefix="/api")
app.include_router(outreach.router)
app.include_router(outreach.router, prefix="/api")

# Alias for /api/ats/check
@app.post("/api/ats/check", response_model=ats.ATSCheckResult, tags=["ats"])
def api_ats_check(payload: ats.ATSCheckRequest, db=Depends(ats.get_db)):
    return ats.check_ats(payload, db)

# Aliases for authenticity checker
@app.post("/api/jobs/authenticity-check", response_model=authenticity.AuthenticityReport, tags=["authenticity"])
@app.post("/api/authenticity/check", response_model=authenticity.AuthenticityReport, tags=["authenticity"])
def api_authenticity_check(payload: authenticity.AuthenticityCheckRequest):
    return authenticity.check_authenticity(payload)

# Alias for /api/resume/suggest-edits
@app.post("/api/resume/suggest-edits", response_model=matcher.SuggestEditsOut, tags=["matcher"])
def api_suggest_edits(payload: matcher.SuggestEditsRequest, db=Depends(matcher.get_db)):
    return matcher.suggest_resume_edits(payload, db)

# Aliases for company insights
@app.post("/api/company/insights", response_model=insights.CompanyInsightsOut, tags=["insights"])
@app.post("/api/insights/company", response_model=insights.CompanyInsightsOut, tags=["insights"])
def api_company_insights(payload: insights.CompanyInsightsRequest, db=Depends(insights.get_db)):
    return insights.analyze_company(payload, db)




@app.get("/")
def root(request: Request):
    """Serves the rich web UI for browsers, or API status for JSON clients."""
    accept_header = request.headers.get("accept", "")
    index_file = STATIC_DIR / "index.html"
    no_cache_headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    if "text/html" in accept_header and index_file.exists():
        return FileResponse(index_file, headers=no_cache_headers)
    if index_file.exists():
        return FileResponse(index_file, headers=no_cache_headers)
    return {
        "name": "malloc() API",
        "status": "online",
        "version": "0.1.0-stage1",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/api")
def api_info():
    """Explicit JSON API info endpoint."""
    return {
        "name": "malloc() API",
        "status": "online",
        "version": "0.1.0-stage1",
        "docs": "/docs",
        "health": "/health",
    }


from app.config import settings
from pydantic import BaseModel


class UpdateSettingsRequest(BaseModel):
    llm_provider: str | None = None
    groq_api_key: str | None = None
    anthropic_api_key: str | None = None
    groq_model: str | None = None


@app.get("/api/settings")
def get_settings():
    return {
        "llm_provider": settings.llm_provider,
        "groq_api_key_configured": bool(settings.groq_api_key and settings.groq_api_key.strip()),
        "anthropic_api_key_configured": bool(settings.anthropic_api_key and settings.anthropic_api_key.strip()),
        "groq_model": settings.groq_model,
        "memora_model": settings.memora_model,
    }


@app.post("/api/settings")
def update_settings(payload: UpdateSettingsRequest):
    env_file = Path(__file__).parent.parent / ".env"
    env_vars = {}

    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip()

    if payload.llm_provider is not None:
        settings.llm_provider = payload.llm_provider
        env_vars["LLM_PROVIDER"] = payload.llm_provider

    if payload.groq_api_key is not None:
        key = payload.groq_api_key.strip()
        settings.groq_api_key = key
        env_vars["GROQ_API_KEY"] = key

    if payload.anthropic_api_key is not None:
        key = payload.anthropic_api_key.strip()
        settings.anthropic_api_key = key
        env_vars["ANTHROPIC_API_KEY"] = key

    if payload.groq_model is not None:
        settings.groq_model = payload.groq_model
        env_vars["GROQ_MODEL"] = payload.groq_model

    # Write back to .env
    lines = [f"{k}={v}" for k, v in env_vars.items()]
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "status": "updated",
        "llm_provider": settings.llm_provider,
        "groq_api_key_configured": bool(settings.groq_api_key and settings.groq_api_key.strip()),
        "anthropic_api_key_configured": bool(settings.anthropic_api_key and settings.anthropic_api_key.strip()),
    }


@app.get("/health")
def health():
    return {"status": "ok", "stage": 1}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    logging.getLogger("memora.main").exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
