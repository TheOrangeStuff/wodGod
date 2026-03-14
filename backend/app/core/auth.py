"""JWT authentication and password hashing."""

from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc)
        + timedelta(hours=settings.JWT_EXPIRE_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """FastAPI dependency: extract user_id from JWT Bearer token."""
    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return user_id


def get_current_user(
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """FastAPI dependency: return full user row."""
    with get_db() as conn:
        with conn.cursor() as cur:
            # Check if unit_system column exists (handles pre-migration DB)
            cur.execute(
                """SELECT EXISTS(
                       SELECT 1 FROM information_schema.columns
                       WHERE table_name = 'users' AND column_name = 'unit_system'
                   )"""
            )
            has_unit_system = cur.fetchone()[0]

            if has_unit_system:
                cur.execute(
                    """SELECT id, username, name, age, weight_kg, height_cm,
                              sex, training_age_yr, equipment, unit_system,
                              profile_complete
                       FROM users WHERE id = %s""",
                    (user_id,),
                )
            else:
                cur.execute(
                    """SELECT id, username, name, age, weight_kg, height_cm,
                              sex, training_age_yr, equipment,
                              profile_complete
                       FROM users WHERE id = %s""",
                    (user_id,),
                )

            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=401, detail="User not found")
            result = dict(row)
            if not has_unit_system:
                result["unit_system"] = "metric"
            return result
