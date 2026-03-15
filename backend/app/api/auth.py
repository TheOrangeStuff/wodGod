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
from app.models.auth import RegisterInput, LoginInput, ProfileSetupInput, ProfileUpdateInput

router = APIRouter(prefix="/auth", tags=["auth"])


def _has_column(cur, column_name: str) -> bool:
    """Check if a column exists on the users table."""
    cur.execute(
        """SELECT EXISTS(
               SELECT 1 FROM information_schema.columns
               WHERE table_name = 'users' AND column_name = %s
           )""",
        (column_name,),
    )
    return cur.fetchone()["exists"]


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
            has_units = _has_column(cur, "unit_system")
            if has_units:
                cur.execute(
                    """UPDATE users SET
                           name = %s, age = %s, weight_kg = %s, height_cm = %s,
                           sex = %s, training_age_yr = %s, equipment = %s,
                           unit_system = %s, profile_complete = true
                       WHERE id = %s
                       RETURNING id""",
                    (
                        data.name, data.age, data.weight_kg, data.height_cm,
                        data.sex, data.training_age_yr,
                        json.dumps(data.equipment), data.unit_system, user_id,
                    ),
                )
            else:
                cur.execute(
                    """UPDATE users SET
                           name = %s, age = %s, weight_kg = %s, height_cm = %s,
                           sex = %s, training_age_yr = %s, equipment = %s,
                           profile_complete = true
                       WHERE id = %s
                       RETURNING id""",
                    (
                        data.name, data.age, data.weight_kg, data.height_cm,
                        data.sex, data.training_age_yr,
                        json.dumps(data.equipment), user_id,
                    ),
                )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")

            # Auto-create an accumulation program if none exists
            cur.execute(
                "SELECT id FROM programs WHERE user_id = %s AND is_active = true",
                (user_id,),
            )
            existing_program = cur.fetchone()
            program = None
            if not existing_program:
                cur.execute(
                    """INSERT INTO programs (user_id, phase, week_number, is_active)
                       VALUES (%s, 'accumulation', 1, true)
                       RETURNING id""",
                    (user_id,),
                )
                program = cur.fetchone()

    return {
        "profile_complete": True,
        "program_created": program is not None,
    }


@router.put("/profile")
def update_profile(
    data: ProfileUpdateInput,
    user_id: str = Depends(get_current_user_id),
):
    """Update user profile fields. Only provided fields are changed."""
    with get_db() as conn:
        with conn.cursor() as cur:
            # Handle username change — check uniqueness
            if data.username is not None:
                cur.execute(
                    "SELECT id FROM users WHERE username = %s AND id != %s",
                    (data.username, user_id),
                )
                if cur.fetchone():
                    raise HTTPException(status_code=409, detail="Username already taken")

            # Build dynamic SET clause for non-None fields
            has_units = _has_column(cur, "unit_system")
            updates = []
            params = []
            field_map = [
                ("name", "name"),
                ("age", "age"),
                ("weight_kg", "weight_kg"),
                ("height_cm", "height_cm"),
                ("sex", "sex"),
                ("training_age_yr", "training_age_yr"),
                ("username", "username"),
            ]
            if has_units:
                field_map.append(("unit_system", "unit_system"))
            for field, column in field_map:
                val = getattr(data, field)
                if val is not None:
                    updates.append(f"{column} = %s")
                    params.append(val)

            # Handle password separately (needs hashing)
            if data.password is not None:
                updates.append("password_hash = %s")
                params.append(hash_password(data.password))

            if not updates:
                raise HTTPException(status_code=422, detail="No fields to update")

            params.append(user_id)
            cur.execute(
                f"""UPDATE users SET {', '.join(updates)}
                    WHERE id = %s RETURNING id""",
                params,
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="User not found")

    return {"updated": True}


@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    """Return current authenticated user profile."""
    return user
