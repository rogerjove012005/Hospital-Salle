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
      medico_id TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    with engine().begin() as conn:
        conn.execute(text(sql))

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                  token TEXT PRIMARY KEY,
                  user_id UUID NOT NULL REFERENCES app_users(user_id) ON DELETE CASCADE,
                  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  expires_at TIMESTAMPTZ NOT NULL,
                  used_at TIMESTAMPTZ
                );
                CREATE INDEX IF NOT EXISTS password_reset_tokens_user_id_idx ON password_reset_tokens(user_id);
                CREATE INDEX IF NOT EXISTS password_reset_tokens_expires_at_idx ON password_reset_tokens(expires_at);
                """
            )
        )

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
                  ADD COLUMN IF NOT EXISTS date_of_birth DATE,
                  ADD COLUMN IF NOT EXISTS department TEXT,
                  ADD COLUMN IF NOT EXISTS primary_diagnosis TEXT;
                """
            )
        )

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS medicos (
                  medico_id TEXT PRIMARY KEY,
                  full_name TEXT NOT NULL,
                  phone TEXT,
                  date_of_birth DATE,
                  sex TEXT,
                  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
        )

        conn.execute(
            text("ALTER TABLE app_users ADD COLUMN IF NOT EXISTS medico_id TEXT;"),
        )
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                  IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'app_users_medico_id_fkey'
                  ) THEN
                    ALTER TABLE app_users
                      ADD CONSTRAINT app_users_medico_id_fkey
                      FOREIGN KEY (medico_id) REFERENCES medicos(medico_id);
                  END IF;
                END $$;
                """
            )
        )

        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS patients_phone_uidx ON patients(phone) WHERE phone IS NOT NULL;"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS medicos_phone_uidx ON medicos(phone) WHERE phone IS NOT NULL;"))

        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS patient_id_seq;"))
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS medico_id_seq;"))

        conn.execute(
            text("ALTER TABLE app_users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;"),
        )


def init_import_schema() -> None:
    """Tablas de ingesta CSV y agregados Spark (idempotente)."""
    ddl = """
    CREATE TABLE IF NOT EXISTS csv_import_batches (
      batch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID NOT NULL REFERENCES app_users(user_id) ON DELETE CASCADE,
      source_filename TEXT,
      row_count INTEGER NOT NULL DEFAULT 0,
      sha256 TEXT,
      quality_summary JSONB,
      ingest_status TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS csv_import_batches_user_sha_idx
      ON csv_import_batches(user_id, sha256);

    CREATE TABLE IF NOT EXISTS csv_import_rows (
      row_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      batch_id UUID NOT NULL REFERENCES csv_import_batches(batch_id) ON DELETE CASCADE,
      position INTEGER NOT NULL,
      fields JSONB NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      UNIQUE (batch_id, position)
    );
    CREATE INDEX IF NOT EXISTS csv_import_rows_batch_idx ON csv_import_rows(batch_id);

    CREATE TABLE IF NOT EXISTS csv_spark_batch_row_counts (
      batch_id TEXT PRIMARY KEY,
      row_count BIGINT NOT NULL,
      computed_at TIMESTAMPTZ
    );

    CREATE TABLE IF NOT EXISTS csv_spark_run_summary (
      id INTEGER PRIMARY KEY,
      computed_at TIMESTAMPTZ,
      total_rows BIGINT,
      batches_with_rows INTEGER
    );
    """
    with engine().begin() as conn:
        conn.execute(text(ddl))

