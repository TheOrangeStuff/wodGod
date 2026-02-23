"""Program management endpoints."""

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.database import get_db

router = APIRouter(prefix="/programs", tags=["programs"])


@router.get("/active")
def get_active_program():
    """Get the current active program."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, user_id, start_date, phase, week_number,
                          is_active, created_at, updated_at
                   FROM programs
                   WHERE user_id = %s AND is_active = true
                   ORDER BY created_at DESC LIMIT 1""",
                (settings.DEFAULT_USER_ID,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(
                    status_code=404, detail="No active program"
                )
            return dict(row)


@router.post("/advance-week")
def advance_week():
    """Advance the active program to the next week."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE programs
                   SET week_number = week_number + 1
                   WHERE user_id = %s AND is_active = true
                   RETURNING id, week_number, phase""",
                (settings.DEFAULT_USER_ID,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(
                    status_code=404, detail="No active program"
                )
            return {
                "program_id": str(row["id"]),
                "new_week": row["week_number"],
                "phase": row["phase"],
            }


@router.post("/set-phase")
def set_phase(phase: str):
    """Manually set the program phase."""
    valid_phases = {"accumulation", "intensification", "realization", "deload"}
    if phase not in valid_phases:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid phase. Must be one of: {valid_phases}",
        )

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE programs
                   SET phase = %s::program_phase
                   WHERE user_id = %s AND is_active = true
                   RETURNING id, week_number, phase""",
                (phase, settings.DEFAULT_USER_ID),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(
                    status_code=404, detail="No active program"
                )
            return {
                "program_id": str(row["id"]),
                "week_number": row["week_number"],
                "phase": row["phase"],
            }


@router.get("/movements")
def list_movements(category: str | None = None):
    """List all movements in the taxonomy."""
    with get_db() as conn:
        with conn.cursor() as cur:
            if category:
                cur.execute(
                    """SELECT id, name, category, is_barbell, is_unilateral
                       FROM movements
                       WHERE category = %s::movement_category
                       ORDER BY name""",
                    (category,),
                )
            else:
                cur.execute(
                    """SELECT id, name, category, is_barbell, is_unilateral
                       FROM movements ORDER BY category, name"""
                )
            return [dict(r) for r in cur.fetchall()]


@router.get("/strength")
def get_strength_metrics():
    """Get current strength metrics."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT m.name AS movement, m.category,
                          sm.training_max, sm.estimated_1rm, sm.tested_at
                   FROM strength_metrics sm
                   JOIN movements m ON m.id = sm.movement_id
                   WHERE sm.user_id = %s
                   ORDER BY m.category, m.name""",
                (settings.DEFAULT_USER_ID,),
            )
            return [dict(r) for r in cur.fetchall()]
