"""wodGod — CrossFit Training Engine API."""

import logging
import os

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import auth, workouts, logs, programs, settings, stats
from app.core.bootstrap import bootstrap_database
from app.core.migrate import run_migrations

logger = logging.getLogger("wodgod")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Bootstrap database and run migrations on startup."""
    try:
        logger.info("Bootstrapping database...")
        bootstrap_database()
        logger.info("Running database migrations...")
        run_migrations()
        logger.info("Migrations complete — startup OK.")
    except Exception:
        logger.exception("FATAL: Database bootstrap/migration failed. The app will not serve requests correctly.")
        raise
    yield


app = FastAPI(
    title="wodGod",
    description="Stateful CrossFit programming engine with LLM-driven workout generation",
    version="0.2.0",
    lifespan=lifespan,
)

class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.endswith(('.js', '.css', '.html')) or request.url.path == '/':
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response

app.add_middleware(NoCacheStaticMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(workouts.router)
app.include_router(logs.router)
app.include_router(programs.router)
app.include_router(settings.router)
app.include_router(stats.router)


@app.get("/health")
def health():
    """Health check endpoint."""
    from app.core.database import get_db

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    return {"status": "ok", "database": db_status}


# Serve frontend static files — mount LAST so API routes take priority
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")
