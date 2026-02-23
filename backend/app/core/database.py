import psycopg2
import psycopg2.extras
from contextlib import contextmanager

from app.core.config import settings

psycopg2.extras.register_uuid()


def get_connection():
    return psycopg2.connect(
        settings.DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
