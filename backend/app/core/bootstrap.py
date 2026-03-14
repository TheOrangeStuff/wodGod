"""Bootstrap the PostgreSQL database: create DB and enable extensions."""

import logging

import psycopg2
from psycopg2 import sql

from app.core.config import settings

logger = logging.getLogger("wodgod.bootstrap")


def _target_dsn():
    return (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )


def _try_connect_target():
    """Try to connect directly to the target database.
    Returns True if the database already exists, False otherwise."""
    try:
        conn = psycopg2.connect(_target_dsn())
        conn.close()
        return True
    except psycopg2.OperationalError as e:
        if "does not exist" in str(e):
            return False
        # Other connection errors (wrong password, host unreachable, etc.)
        raise


def _create_database():
    """Connect to the 'postgres' admin database and CREATE the target DB."""
    target_db = settings.POSTGRES_DB
    admin_dsn = (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/postgres"
    )

    conn = psycopg2.connect(admin_dsn)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (target_db,)
            )
            if cur.fetchone():
                logger.info("Database '%s' already exists.", target_db)
            else:
                cur.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(target_db)
                    )
                )
                logger.info("Created database '%s'.", target_db)
    finally:
        conn.close()


def _enable_extensions():
    """Enable required extensions on the target database."""
    conn = psycopg2.connect(_target_dsn())
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
            logger.info("Extension 'pgcrypto' enabled on '%s'.", settings.POSTGRES_DB)
    finally:
        conn.close()


def bootstrap_database():
    """Ensure the target database exists and has required extensions.

    First tries to connect to the target database directly. If it doesn't
    exist, connects to the 'postgres' admin database to create it. Falls
    back gracefully when the admin database is not accessible.
    """
    target_db = settings.POSTGRES_DB

    logger.info(
        "Bootstrapping: ensuring database '%s' exists on %s:%s",
        target_db,
        settings.POSTGRES_HOST,
        settings.POSTGRES_PORT,
    )

    # 1. Check if target database already exists
    if _try_connect_target():
        logger.info("Database '%s' is reachable.", target_db)
        _enable_extensions()
        return

    # 2. Target DB doesn't exist — try to create it via admin connection
    logger.info("Database '%s' does not exist, attempting to create it...", target_db)
    try:
        _create_database()
    except psycopg2.OperationalError as e:
        raise RuntimeError(
            f"Database '{target_db}' does not exist and could not be created. "
            f"Cannot connect to the 'postgres' admin database on "
            f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT} to issue "
            f"CREATE DATABASE. Either create the database manually or ensure "
            f"the configured user has access to the 'postgres' database. "
            f"Original error: {e}"
        ) from e
    except psycopg2.Error as e:
        raise RuntimeError(
            f"Database '{target_db}' does not exist and creation failed: {e}. "
            f"Please create the database manually: "
            f"CREATE DATABASE {target_db};"
        ) from e

    # 3. Verify the database was actually created
    if not _try_connect_target():
        raise RuntimeError(
            f"Database '{target_db}' still does not exist after creation attempt. "
            f"The configured PostgreSQL user may lack CREATE DATABASE privileges. "
            f"Please create the database manually: CREATE DATABASE {target_db};"
        )

    _enable_extensions()
    logger.info("Database '%s' bootstrapped successfully.", target_db)
