"""Stats endpoints for charts and analytics."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.core.auth import get_current_user_id

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def get_stats(user_id: str = Depends(get_current_user_id)):
    """Return aggregated stats for the charts page."""
    today = date.today()

    with get_db() as conn:
        with conn.cursor() as cur:
            # RPE trend: last 30 logged workouts
            cur.execute(
                """SELECT w.scheduled_date AS date, wl.actual_rpe AS rpe
                   FROM workout_logs wl
                   JOIN workouts w ON w.id = wl.workout_id
                   WHERE wl.user_id = %s
                   ORDER BY w.scheduled_date ASC
                   LIMIT 30""",
                (user_id,),
            )
            rpe_trend = []
            for r in cur.fetchall():
                rpe_trend.append({
                    "date": r["date"].isoformat() if hasattr(r["date"], "isoformat") else str(r["date"]),
                    "rpe": float(r["rpe"]) if r["rpe"] is not None else None,
                })
            # Filter out null RPEs
            rpe_trend = [r for r in rpe_trend if r["rpe"] is not None]

            # Movement balance: last 21 days
            cutoff_21 = today - timedelta(days=21)
            cur.execute(
                """SELECT w.focus AS category, COUNT(*) AS count
                   FROM workouts w
                   LEFT JOIN programs p ON p.id = w.program_id
                   WHERE (
                       (p.user_id = %s AND p.is_active = true)
                       OR (w.user_id = %s AND w.is_custom = true)
                   )
                   AND w.scheduled_date >= %s
                   AND w.scheduled_date <= %s
                   GROUP BY w.focus
                   ORDER BY count DESC""",
                (user_id, user_id, cutoff_21, today),
            )
            movement_balance = [
                {"category": r["category"], "count": r["count"]}
                for r in cur.fetchall()
            ]

            # Training volume per week: last 8 weeks
            cutoff_8w = today - timedelta(weeks=8)
            cur.execute(
                """SELECT date_trunc('week', w.scheduled_date)::date AS week_start,
                          COUNT(*) AS sessions
                   FROM workout_logs wl
                   JOIN workouts w ON w.id = wl.workout_id
                   WHERE wl.user_id = %s
                     AND w.scheduled_date >= %s
                   GROUP BY week_start
                   ORDER BY week_start""",
                (user_id, cutoff_8w),
            )
            volume_per_week = []
            for r in cur.fetchall():
                ws = r["week_start"]
                label = ws.strftime("%b %d") if hasattr(ws, "strftime") else str(ws)
                volume_per_week.append({
                    "week_label": label,
                    "sessions": r["sessions"],
                })

    return {
        "rpe_trend": rpe_trend,
        "movement_balance": movement_balance,
        "volume_per_week": volume_per_week,
    }
