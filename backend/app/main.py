"""wodGod — CrossFit Training Engine API."""

from fastapi import FastAPI

from app.api import workouts, logs, programs

app = FastAPI(
    title="wodGod",
    description="Stateful CrossFit programming engine with LLM-driven workout generation",
    version="0.1.0",
)

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
