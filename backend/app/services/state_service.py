"""Assembles SYSTEM_STATE JSON by calling the SQL function."""

import json

from app.core.database import get_db
from app.core.config import settings


def get_system_state(user_id: str | None = None) -> dict:
    """Call fn_build_system_state and return the assembled JSON."""
    uid = user_id or settings.DEFAULT_USER_ID

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT fn_build_system_state(%s) AS state", (uid,))
            row = cur.fetchone()

    state = row["state"]
    if isinstance(state, str):
        state = json.loads(state)
    return state


def get_allowed_movements() -> list[str]:
    """Return the full movement vocabulary from the DB."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM movements ORDER BY category, name")
            return [r["name"] for r in cur.fetchall()]


def get_movement_categories() -> dict[str, str]:
    """Return movement -> category mapping."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name, category FROM movements")
            return {r["name"]: r["category"] for r in cur.fetchall()}
