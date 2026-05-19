import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db.database import database_connected, database_enabled, get_database_url, init_db
from backend.routes.authRoutes import router as auth_router
from backend.routes.logRoutes import router as log_router
from backend.routes.platformRoutes import router as platform_router


app = FastAPI(
    title="AI Log Analyzer for DevOps",
    description="DevOps-focused log diagnostics API with AI-swappable analysis.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(log_router)
app.include_router(platform_router)


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/health")
async def health_check():
    db_url = get_database_url()
    return {
        "status": "ok",
        "service": "AI Log Analyzer for DevOps",
        "storage": "postgres" if database_connected() else "memory",
        "database_configured": database_enabled(),
        "database_url": _safe_database_url(db_url),
        "ai_engine": "openai" if os.getenv("OPENAI_API_KEY") else "local-ml",
        "ai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini") if os.getenv("OPENAI_API_KEY") else None,
    }


def _safe_database_url(database_url: str | None) -> str | None:
    if not database_url:
        return None
    if "@" not in database_url or "://" not in database_url:
        return database_url
    scheme, rest = database_url.split("://", 1)
    _, host = rest.rsplit("@", 1)
    return f"{scheme}://***:***@{host}"
