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

        # Evolve schema for self-registration (medicos sin patient_id + datos de paciente)
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                  IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'app_users'
                      AND column_name = 'patient_id'
                      AND is_nullable = 'NO'
                  ) THEN
                    EXECUTE 'ALTER TABLE app_users ALTER COLUMN patient_id DROP NOT NULL';
                  END IF;
                END $$;
                """
            )
        )

        conn.execute(
            text(
                """
                ALTER TABLE patients
                  ADD COLUMN IF NOT EXISTS full_name TEXT,
                  ADD COLUMN IF NOT EXISTS phone TEXT,
                  ADD COLUMN IF NOT EXISTS date_of_birth DATE;
                """
            )
        )

        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS patients_phone_uidx ON patients(phone) WHERE phone IS NOT NULL;"))

        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS patient_id_seq;"))
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS medico_id_seq;"))

