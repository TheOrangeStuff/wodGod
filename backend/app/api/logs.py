"""Workout logging and daily readiness endpoints."""

import json
from datetime import date
from fastapi import APIRouter, HTTPException, Depends

from app.core.database import get_db
from app.core.auth import get_current_user_id
from app.models.workout import WorkoutLogInput, ReadinessInput

router = APIRouter(tags=["logs"])


# ============================================================
# WORKOUT LOGS
# ============================================================

@router.post("/workouts/{workout_id}/log")
def log_workout(
    workout_id: str,
    log_input: WorkoutLogInput,
    user_id: str = Depends(get_current_user_id),
):
    """Record a workout completion log."""
    with get_db() as conn:
        with conn.cursor() as cur:
            # Verify workout exists and belongs to this user
            cur.execute(
                """SELECT w.id FROM workouts w
                   JOIN programs p ON p.id = w.program_id
                   WHERE w.id = %s AND p.user_id = %s""",
                (workout_id, user_id),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Workout not found")

            # Check for duplicate log
            cur.execute(
                """SELECT id FROM workout_logs
                   WHERE workout_id = %s AND user_id = %s""",
                (workout_id, user_id),
            )
            if cur.fetchone():
                raise HTTPException(
                    status_code=409, detail="Workout already logged"
                )

            cur.execute(
                """INSERT INTO workout_logs
                   (workout_id, user_id, actual_rpe, missed_reps,
                    performance_json, notes)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING id, completed_at""",
                (
                    workout_id,
                    user_id,
                    log_input.actual_rpe,
                    log_input.missed_reps,
                    json.dumps(log_input.performance_json),
                    log_input.notes,
                ),
            )
            row = cur.fetchone()
            return {
                "log_id": str(row["id"]),
                "completed_at": row["completed_at"].isoformat(),
            }


@router.put("/logs/{log_id}")
def update_log(
    log_id: str,
    log_input: WorkoutLogInput,
    user_id: str = Depends(get_current_user_id),
):
    """Update an existing workout log."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE workout_logs
                   SET actual_rpe = %s, missed_reps = %s,
                       performance_json = %s, notes = %s
                   WHERE id = %s AND user_id = %s
                   RETURNING id, completed_at""",
                (
                    log_input.actual_rpe,
                    log_input.missed_reps,
                    json.dumps(log_input.performance_json),
                    log_input.notes,
                    log_id,
                    user_id,
                ),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Log not found")
            return {
                "log_id": str(row["id"]),
                "completed_at": row["completed_at"].isoformat(),
            }


@router.get("/logs")
def list_logs(limit: int = 20, user_id: str = Depends(get_current_user_id)):
    """List recent workout logs."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT wl.id, wl.workout_id, wl.actual_rpe, wl.missed_reps,
                          wl.completed_at, wl.notes, wl.performance_json,
                          w.focus, w.program_week, w.day_index,
                          w.workout_json, w.scheduled_date
                   FROM workout_logs wl
                   JOIN workouts w ON w.id = wl.workout_id
                   WHERE wl.user_id = %s
                   ORDER BY wl.completed_at DESC
                   LIMIT %s""",
                (user_id, limit),
            )
            return [dict(r) for r in cur.fetchall()]


# ============================================================
# DAILY READINESS
# ============================================================

@router.post("/readiness")
def submit_readiness(
    readiness: ReadinessInput,
    user_id: str = Depends(get_current_user_id),
):
    """Submit daily readiness score. Upserts for today."""
    today = date.today()

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO daily_readiness
                   (user_id, date, readiness_score, sleep_quality, soreness, stress, notes)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (user_id, date)
                   DO UPDATE SET
                       readiness_score = EXCLUDED.readiness_score,
                       sleep_quality = EXCLUDED.sleep_quality,
                       soreness = EXCLUDED.soreness,
                       stress = EXCLUDED.stress,
                       notes = EXCLUDED.notes
                   RETURNING id""",
                (
                    user_id,
                    today,
                    readiness.readiness_score,
                    readiness.sleep_quality,
                    readiness.soreness,
                    readiness.stress,
                    readiness.notes,
                ),
            )
            row = cur.fetchone()
            return {"readiness_id": row["id"], "date": today.isoformat()}


@router.get("/readiness")
def get_readiness(days: int = 7, user_id: str = Depends(get_current_user_id)):
    """Get recent readiness scores."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT date, readiness_score, sleep_quality, soreness, stress, notes
                   FROM daily_readiness
                   WHERE user_id = %s
                   ORDER BY date DESC
                   LIMIT %s""",
                (user_id, days),
            )
            return [dict(r) for r in cur.fetchall()]
