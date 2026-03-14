"""Bootstrap the PostgreSQL database: create DB and enable extensions."""

import logging

import psycopg2
from psycopg2 import sql

from app.core.config import settings

logger = logging.getLogger("wodgod.bootstrap")


def bootstrap_database():
    """Connect to the Postgres server, create the target database if it
    doesn't exist, and enable required extensions (pgcrypto).

    Connects to the default ``postgres`` database using the configured
    credentials, then switches to the target database for extension setup.
    """
    target_db = settings.POSTGRES_DB

    # Connect to the default 'postgres' database to issue CREATE DATABASE
    admin_dsn = (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/postgres"
    )

    logger.info(
        "Bootstrapping: ensuring database '%s' exists on %s:%s",
        target_db,
        settings.POSTGRES_HOST,
        settings.POSTGRES_PORT,
    )

    conn = psycopg2.connect(admin_dsn)
    conn.autocommit = True  # CREATE DATABASE cannot run inside a transaction
    try:
        with conn.cursor() as cur:
            # Check if target database already exists
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

    # Now connect to the target database and enable pgcrypto
    target_dsn = (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{target_db}"
    )
    conn = psycopg2.connect(target_dsn)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
            logger.info("Extension 'pgcrypto' enabled on '%s'.", target_db)
    finally:
        conn.close()
