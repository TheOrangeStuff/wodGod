"""Workout generation and management endpoints."""

import json
from datetime import date as date_type

from fastapi import APIRouter, HTTPException, Depends

from app.core.database import get_db
from app.core.auth import get_current_user_id
from app.models.workout import WorkoutPrescription, CustomWorkoutInput
from app.services.state_service import get_system_state
from app.services.llm_service import generate_workout, parse_custom_workout, MAX_RETRIES
from app.services.validation_service import parse_and_validate

router = APIRouter(prefix="/workouts", tags=["workouts"])


@router.get("/state")
def get_current_state(user_id: str = Depends(get_current_user_id)):
    """Return the current SYSTEM_STATE JSON for debugging/inspection."""
    return get_system_state(user_id)


@router.post("/custom")
async def create_custom_workout(
    input: CustomWorkoutInput,
    user_id: str = Depends(get_current_user_id),
):
    """Create a custom workout from a freeform description.

    Attempts LLM parsing to extract structured data (focus, RPE, CNS load).
    Falls back to sensible defaults if LLM is unavailable.
    Auto-creates a workout log for past-dated workouts.
    """
    try:
        scheduled_date = date_type.fromisoformat(input.scheduled_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format. Use YYYY-MM-DD.")

    # Try LLM parsing for structured data
    parsed = await parse_custom_workout(input.description)

    if parsed:
        focus = parsed["focus"]
        intensity_rpe = parsed["intensity_target_rpe"]
        cns_load = parsed["cns_load"]
        workout_json = {
            "focus": focus,
            "intensity_target_rpe": intensity_rpe,
            "time_domain": parsed["time_domain"],
            "cns_load": cns_load,
            "summary": parsed["summary"],
            "custom_description": input.description,
        }
    else:
        # Fallback: store without structured data
        focus = "Custom"
        intensity_rpe = 5.0
        cns_load = "low"
        workout_json = {
            "focus": focus,
            "intensity_target_rpe": intensity_rpe,
            "time_domain": "Unknown",
            "cns_load": cns_load,
            "summary": input.description[:200],
            "custom_description": input.description,
        }

    today = date_type.today()

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO workouts
                   (user_id, program_id, program_week, day_index, focus,
                    intensity_target_rpe, cns_load, workout_json,
                    scheduled_date, custom_description, is_custom)
                   VALUES (%s, NULL, NULL, NULL, %s, %s, %s, %s, %s, %s, true)
                   RETURNING id""",
                (
                    user_id,
                    focus,
                    intensity_rpe,
                    cns_load,
                    json.dumps(workout_json),
                    scheduled_date,
                    input.description,
                ),
            )
            workout_id = str(cur.fetchone()["id"])

            # Auto-log past and current-day workouts as complete
            if scheduled_date <= today:
                cur.execute(
                    """INSERT INTO workout_logs
                       (workout_id, user_id, actual_rpe, missed_reps,
                        performance_json, notes, completed_at)
                       VALUES (%s, %s, %s, 0, '{}'::jsonb, %s, %s)
                       RETURNING id, completed_at""",
                    (
                        workout_id,
                        user_id,
                        intensity_rpe,
                        f"Custom: {input.description[:500]}",
                        scheduled_date.isoformat() + "T12:00:00",
                    ),
                )

            # Determine status
            if scheduled_date < today:
                status = "COMPLETE"
            elif scheduled_date == today:
                status = "COMPLETE"
            else:
                status = "UPCOMING"

            return {
                "workout_id": workout_id,
                "focus": focus,
                "status": status,
                "llm_parsed": parsed is not None,
                "workout_json": workout_json,
            }


@router.post("/generate")
async def generate_workout_endpoint(
    day_index: int = 1,
    program_week: int | None = None,
    user_id: str = Depends(get_current_user_id),
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


@router.post("/generate-week")
async def generate_week(
    days: int = 5,
    user_id: str = Depends(get_current_user_id),
):
    """Generate a full week of workouts (7 days in advance)."""
    from app.services.generation_service import generate_weekly_workouts

    results = await generate_weekly_workouts(user_id, days=days)
    return results


@router.get("/today")
def get_today_workout(user_id: str = Depends(get_current_user_id)):
    """Get today's workout (View WOD page)."""
    from datetime import date

    today = date.today()
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT w.id, w.program_week, w.day_index, w.focus,
                          w.intensity_target_rpe, w.cns_load, w.workout_json,
                          w.scheduled_date, w.created_at
                   FROM workouts w
                   JOIN programs p ON p.id = w.program_id
                   WHERE p.user_id = %s AND p.is_active = true
                     AND w.scheduled_date = %s""",
                (user_id, today),
            )
            row = cur.fetchone()
            if not row:
                return {"workout": None, "message": "No workout scheduled for today"}

            # Check if already logged
            cur.execute(
                """SELECT id, actual_rpe, completed_at
                   FROM workout_logs WHERE workout_id = %s AND user_id = %s""",
                (row["id"], user_id),
            )
            log = cur.fetchone()

            return {
                "workout": dict(row),
                "logged": log is not None,
                "log": dict(log) if log else None,
            }


@router.get("/calendar")
def get_calendar(user_id: str = Depends(get_current_user_id)):
    """Get 7-day upcoming workout calendar."""
    from datetime import date, timedelta

    today = date.today()
    end = today + timedelta(days=6)
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT w.id, w.program_week, w.day_index, w.focus,
                          w.intensity_target_rpe, w.cns_load, w.workout_json,
                          w.scheduled_date
                   FROM workouts w
                   JOIN programs p ON p.id = w.program_id
                   WHERE p.user_id = %s AND p.is_active = true
                     AND w.scheduled_date BETWEEN %s AND %s
                   ORDER BY w.scheduled_date""",
                (user_id, today, end),
            )
            workouts = [dict(r) for r in cur.fetchall()]

            # Get log status for each
            workout_ids = [w["id"] for w in workouts]
            logged_ids = set()
            if workout_ids:
                cur.execute(
                    """SELECT workout_id FROM workout_logs
                       WHERE user_id = %s AND workout_id = ANY(%s)""",
                    (user_id, workout_ids),
                )
                logged_ids = {r["workout_id"] for r in cur.fetchall()}

            for w in workouts:
                w["logged"] = w["id"] in logged_ids

            return workouts


@router.get("/all")
def get_all_workouts(user_id: str = Depends(get_current_user_id)):
    """Get all workouts with status labels: TODAY, COMPLETE, MISSED, UPCOMING."""
    today = date_type.today()
    with get_db() as conn:
        with conn.cursor() as cur:
            # Get program workouts + custom workouts in one query
            cur.execute(
                """SELECT w.id, w.program_week, w.day_index, w.focus,
                          w.intensity_target_rpe, w.cns_load, w.workout_json,
                          w.scheduled_date, w.is_custom, w.custom_description
                   FROM workouts w
                   LEFT JOIN programs p ON p.id = w.program_id
                   WHERE (
                       (p.user_id = %s AND p.is_active = true)
                       OR (w.user_id = %s AND w.is_custom = true)
                   )
                   ORDER BY w.scheduled_date DESC, w.day_index""",
                (user_id, user_id),
            )
            workouts = [dict(r) for r in cur.fetchall()]

            # Get logged workout IDs
            workout_ids = [w["id"] for w in workouts]
            logged_map = {}
            if workout_ids:
                cur.execute(
                    """SELECT wl.workout_id, wl.id as log_id, wl.actual_rpe,
                              wl.missed_reps, wl.completed_at, wl.notes
                       FROM workout_logs wl
                       WHERE wl.user_id = %s AND wl.workout_id = ANY(%s)""",
                    (user_id, workout_ids),
                )
                for r in cur.fetchall():
                    logged_map[r["workout_id"]] = dict(r)

            for w in workouts:
                sd = w["scheduled_date"]
                has_log = w["id"] in logged_map
                if sd == today:
                    w["status"] = "COMPLETE" if has_log else "TODAY"
                elif sd < today:
                    w["status"] = "COMPLETE" if has_log else "MISSED"
                else:
                    w["status"] = "UPCOMING"
                w["log"] = logged_map.get(w["id"])

            return workouts


@router.get("/{workout_id}")
def get_workout(workout_id: str, user_id: str = Depends(get_current_user_id)):
    """Retrieve a stored workout by ID."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT w.id, w.program_id, w.program_week, w.day_index, w.focus,
                          w.intensity_target_rpe, w.cns_load, w.workout_json,
                          w.scheduled_date, w.created_at, w.is_custom,
                          w.custom_description
                   FROM workouts w
                   LEFT JOIN programs p ON p.id = w.program_id
                   WHERE w.id = %s
                     AND (p.user_id = %s OR w.user_id = %s)""",
                (workout_id, user_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Workout not found")
            return dict(row)


@router.get("")
def list_workouts(
    program_id: str | None = None,
    user_id: str = Depends(get_current_user_id),
):
    """List workouts, optionally filtered by program."""
    with get_db() as conn:
        with conn.cursor() as cur:
            if program_id:
                cur.execute(
                    """SELECT w.id, w.program_week, w.day_index, w.focus,
                              w.intensity_target_rpe, w.cns_load, w.scheduled_date
                       FROM workouts w
                       JOIN programs p ON p.id = w.program_id
                       WHERE w.program_id = %s AND p.user_id = %s
                       ORDER BY w.program_week, w.day_index""",
                    (program_id, user_id),
                )
            else:
                cur.execute(
                    """SELECT w.id, w.program_week, w.day_index, w.focus,
                              w.intensity_target_rpe, w.cns_load, w.scheduled_date
                       FROM workouts w
                       JOIN programs p ON p.id = w.program_id
                       WHERE p.user_id = %s AND p.is_active = true
                       ORDER BY w.program_week, w.day_index""",
                    (user_id,),
                )
            return [dict(r) for r in cur.fetchall()]


def _store_workout(
    program_id: str,
    week: int,
    day_index: int,
    prescription: WorkoutPrescription,
    scheduled_date=None,
) -> str:
    """Insert the validated workout into the DB and return its ID."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO workouts
                   (program_id, program_week, day_index, focus,
                    intensity_target_rpe, cns_load, workout_json, scheduled_date)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, COALESCE(%s, CURRENT_DATE))
                   RETURNING id""",
                (
                    program_id,
                    week,
                    day_index,
                    prescription.focus,
                    prescription.intensity_target_rpe,
                    prescription.cns_load.value,
                    json.dumps(prescription.model_dump()),
                    scheduled_date,
                ),
            )
            return str(cur.fetchone()["id"])
