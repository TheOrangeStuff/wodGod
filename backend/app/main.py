"""wodGod — CrossFit Training Engine API."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import auth, workouts, logs, programs

app = FastAPI(
    title="wodGod",
    description="Stateful CrossFit programming engine with LLM-driven workout generation",
    version="0.2.0",
)

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
