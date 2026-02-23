"""Authentication and profile setup endpoints."""

import json
from fastapi import APIRouter, HTTPException, Depends

from app.core.database import get_db
from app.core.auth import (
    hash_password,
    verify_password,
    create_token,
    get_current_user_id,
    get_current_user,
)
from app.models.auth import RegisterInput, LoginInput, ProfileSetupInput

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(data: RegisterInput):
    """Register a new athlete account."""
    with get_db() as conn:
        with conn.cursor() as cur:
            # Check username uniqueness
            cur.execute("SELECT id FROM users WHERE username = %s", (data.username,))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Username already taken")

            pw_hash = hash_password(data.password)
            cur.execute(
                """INSERT INTO users (username, password_hash)
                   VALUES (%s, %s) RETURNING id""",
                (data.username, pw_hash),
            )
            user_id = str(cur.fetchone()["id"])

    token = create_token(user_id)
    return {"user_id": user_id, "token": token, "profile_complete": False}


@router.post("/login")
def login(data: LoginInput):
    """Authenticate and return JWT."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, password_hash, profile_complete FROM users WHERE username = %s",
                (data.username,),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(data.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(str(row["id"]))
    return {
        "user_id": str(row["id"]),
        "token": token,
        "profile_complete": row["profile_complete"],
    }


@router.post("/setup-profile")
def setup_profile(
    data: ProfileSetupInput,
    user_id: str = Depends(get_current_user_id),
):
    """Complete first-time athlete profile setup."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE users SET
                       name = %s, age = %s, weight_kg = %s, height_cm = %s,
                       sex = %s, training_age_yr = %s, equipment = %s,
                       profile_complete = true
                   WHERE id = %s
                   RETURNING id""",
                (
                    data.name,
                    data.age,
                    data.weight_kg,
                    data.height_cm,
                    data.sex,
                    data.training_age_yr,
                    json.dumps(data.equipment),
                    user_id,
                ),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")

            # Auto-create an accumulation program for new athletes
            cur.execute(
                """INSERT INTO programs (user_id, phase, week_number, is_active)
                   VALUES (%s, 'accumulation', 1, true)
                   ON CONFLICT DO NOTHING
                   RETURNING id""",
                (user_id,),
            )
            program = cur.fetchone()

    return {
        "profile_complete": True,
        "program_created": program is not None,
    }


@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    """Return current authenticated user profile."""
    return user
