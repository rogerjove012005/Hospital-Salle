import os
from functools import lru_cache

from sqlalchemy import create_engine, text


@lru_cache(maxsize=1)
def engine():
    database_url = os.environ["DATABASE_URL"]
    return create_engine(database_url, pool_pre_ping=True)


def init_auth_schema() -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS app_users (
      user_id UUID PRIMARY KEY,
      email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      role TEXT NOT NULL,
      patient_id TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    with engine().begin() as conn:
        conn.execute(text(sql))

