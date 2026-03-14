"""Auto-apply database migrations on startup."""

import logging
import os

import psycopg2

from app.core.config import settings

logger = logging.getLogger("wodgod.migrate")

# Ordered list of SQL files to apply (paths relative to the db/ directory)
MIGRATION_FILES = [
    "migrations/001_schema.sql",
    "migrations/002_auth_multiuser.sql",
    "migrations/003_fix_registration_defaults.sql",
    "functions/001_system_state.sql",
    "seeds/001_seed_data.sql",
]

# Locate the db/ directory (copied into the container at /app/db/)
DB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "db")


def _ensure_tracking_table(cur):
    """Create the migration tracking table if it doesn't exist."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)


def run_migrations():
    """Apply any pending SQL migration files, tracked by filename."""
    conn = psycopg2.connect(settings.DATABASE_URL)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            _ensure_tracking_table(cur)
            conn.commit()

            for relpath in MIGRATION_FILES:
                filepath = os.path.join(DB_DIR, relpath)
                if not os.path.isfile(filepath):
                    logger.warning("Migration file not found, skipping: %s", relpath)
                    continue

                # Check if already applied
                cur.execute(
                    "SELECT 1 FROM schema_migrations WHERE filename = %s",
                    (relpath,),
                )
                if cur.fetchone():
                    logger.debug("Already applied: %s", relpath)
                    continue

                # Apply the migration
                logger.info("Applying migration: %s", relpath)
                with open(filepath, "r") as f:
                    sql = f.read()

                cur.execute(sql)
                cur.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)",
                    (relpath,),
                )
                conn.commit()
                logger.info("Applied: %s", relpath)

    except Exception:
        conn.rollback()
        logger.exception("Migration failed — rolling back")
        raise
    finally:
        conn.close()
