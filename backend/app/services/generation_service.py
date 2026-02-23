"""Weekly batch workout generation service.

Generates 7 days of workouts in advance with fixed scheduling.
Missed workouts are skipped — no shifting, no compression.
"""

import json
from datetime import date, timedelta

from app.core.database import get_db
from app.services.state_service import get_system_state
from app.services.llm_service import generate_workout, MAX_RETRIES
from app.services.validation_service import parse_and_validate


async def generate_weekly_workouts(
    user_id: str,
    days: int = 5,
) -> dict:
    """
    Generate a full week of workouts for the given user.

    Args:
        user_id: The authenticated user's ID.
        days: Number of training days per week (default 5, rest days excluded).

    Returns:
        Summary of generated workouts and any errors.
    """
    state = get_system_state(user_id)
    program_id = state["meta"]["program_id"]
    week = state["meta"]["week_number"]

    today = date.today()
    # Calculate the start of the upcoming 7-day window
    # Workouts are scheduled for the next 7 days starting from today
    results = {"generated": [], "skipped": [], "errors": []}

    for day_idx in range(1, days + 1):
        scheduled = today + timedelta(days=day_idx - 1)

        # Check if a workout already exists for this slot
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id FROM workouts
                       WHERE program_id = %s AND program_week = %s AND day_index = %s""",
                    (program_id, week, day_idx),
                )
                if cur.fetchone():
                    results["skipped"].append(
                        {"day_index": day_idx, "reason": "already exists"}
                    )
                    continue

        # Refresh state between workouts (accumulates generated context)
        if day_idx > 1:
            state = get_system_state(user_id)

        # Generate with retries
        generated = False
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                raw_json = await generate_workout(state)
            except Exception as e:
                if attempt == MAX_RETRIES:
                    results["errors"].append(
                        {"day_index": day_idx, "error": f"LLM failed: {e}"}
                    )
                continue

            prescription, validation = parse_and_validate(raw_json, state)

            if validation.valid and prescription is not None:
                # Store with scheduled date
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """INSERT INTO workouts
                               (program_id, program_week, day_index, focus,
                                intensity_target_rpe, cns_load, workout_json,
                                scheduled_date)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                               RETURNING id""",
                            (
                                program_id,
                                week,
                                day_idx,
                                prescription.focus,
                                prescription.intensity_target_rpe,
                                prescription.cns_load.value,
                                json.dumps(prescription.model_dump()),
                                scheduled,
                            ),
                        )
                        workout_id = str(cur.fetchone()["id"])

                results["generated"].append({
                    "workout_id": workout_id,
                    "day_index": day_idx,
                    "scheduled_date": scheduled.isoformat(),
                    "focus": prescription.focus,
                    "warnings": validation.warnings,
                })
                generated = True
                break

            if attempt == MAX_RETRIES:
                results["errors"].append({
                    "day_index": day_idx,
                    "error": f"Validation failed: {validation.errors}",
                })

        if not generated and not any(
            e["day_index"] == day_idx for e in results["errors"]
        ):
            results["errors"].append({
                "day_index": day_idx,
                "error": "Failed to generate after all retries",
            })

    return results
