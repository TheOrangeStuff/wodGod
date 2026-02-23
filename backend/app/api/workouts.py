"""Workout generation and management endpoints."""

import json
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.database import get_db
from app.models.workout import WorkoutPrescription
from app.services.state_service import get_system_state
from app.services.llm_service import generate_workout, MAX_RETRIES
from app.services.validation_service import parse_and_validate

router = APIRouter(prefix="/workouts", tags=["workouts"])


@router.get("/state")
def get_current_state():
    """Return the current SYSTEM_STATE JSON for debugging/inspection."""
    return get_system_state()


@router.post("/generate")
async def generate_workout_endpoint(
    day_index: int = 1,
    program_week: int | None = None,
):
    """
    Generate a new workout using the LLM.

    Flow:
    1. Build SYSTEM_STATE from SQL
    2. Send to LLM
    3. Parse and validate response
    4. Retry up to MAX_RETRIES on validation failure
    5. Store validated workout in DB
    """
    user_id = settings.DEFAULT_USER_ID
    state = get_system_state(user_id)

    week = program_week or state["meta"]["week_number"]
    program_id = state["meta"]["program_id"]

    # Check for existing workout at this slot
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id FROM workouts
                   WHERE program_id = %s AND program_week = %s AND day_index = %s""",
                (program_id, week, day_index),
            )
            existing = cur.fetchone()
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"Workout already exists for week {week}, day {day_index}",
                )

    # LLM generation with retry loop
    last_errors = []
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            raw_json = await generate_workout(state)
        except Exception as e:
            last_errors.append(f"Attempt {attempt}: LLM call failed: {e}")
            continue

        prescription, validation = parse_and_validate(raw_json, state)

        if validation.valid and prescription is not None:
            # Store the validated workout
            workout_id = _store_workout(
                program_id=program_id,
                week=week,
                day_index=day_index,
                prescription=prescription,
            )
            return {
                "workout_id": workout_id,
                "prescription": prescription.model_dump(),
                "warnings": validation.warnings,
                "attempt": attempt,
            }

        last_errors.append(
            f"Attempt {attempt}: {validation.errors}"
        )

    raise HTTPException(
        status_code=422,
        detail={
            "message": "Failed to generate valid workout after retries",
            "errors": last_errors,
        },
    )


@router.get("/{workout_id}")
def get_workout(workout_id: str):
    """Retrieve a stored workout by ID."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, program_id, program_week, day_index, focus,
                          intensity_target_rpe, cns_load, workout_json,
                          scheduled_date, created_at
                   FROM workouts WHERE id = %s""",
                (workout_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Workout not found")
            return dict(row)


@router.get("")
def list_workouts(program_id: str | None = None):
    """List workouts, optionally filtered by program."""
    with get_db() as conn:
        with conn.cursor() as cur:
            if program_id:
                cur.execute(
                    """SELECT id, program_week, day_index, focus,
                              intensity_target_rpe, cns_load, scheduled_date
                       FROM workouts WHERE program_id = %s
                       ORDER BY program_week, day_index""",
                    (program_id,),
                )
            else:
                cur.execute(
                    """SELECT w.id, w.program_week, w.day_index, w.focus,
                              w.intensity_target_rpe, w.cns_load, w.scheduled_date
                       FROM workouts w
                       JOIN programs p ON p.id = w.program_id
                       WHERE p.user_id = %s AND p.is_active = true
                       ORDER BY w.program_week, w.day_index""",
                    (settings.DEFAULT_USER_ID,),
                )
            return [dict(r) for r in cur.fetchall()]


def _store_workout(
    program_id: str,
    week: int,
    day_index: int,
    prescription: WorkoutPrescription,
) -> str:
    """Insert the validated workout into the DB and return its ID."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO workouts
                   (program_id, program_week, day_index, focus,
                    intensity_target_rpe, cns_load, workout_json, scheduled_date)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_DATE)
                   RETURNING id""",
                (
                    program_id,
                    week,
                    day_index,
                    prescription.focus,
                    prescription.intensity_target_rpe,
                    prescription.cns_load.value,
                    json.dumps(prescription.model_dump()),
                ),
            )
            return str(cur.fetchone()["id"])
