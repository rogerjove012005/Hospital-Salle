CREATE TABLE IF NOT EXISTS patients (
  patient_id TEXT PRIMARY KEY,
  age INTEGER,
  sex TEXT,
  full_name TEXT,
  phone TEXT,
  date_of_birth DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Personal médico (independiente de `patients`; los estudios siguen vinculados solo a pacientes)
CREATE TABLE IF NOT EXISTS medicos (
  medico_id TEXT PRIMARY KEY,
  full_name TEXT NOT NULL,
  phone TEXT,
  date_of_birth DATE,
  sex TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE SEQUENCE IF NOT EXISTS patient_id_seq;
CREATE SEQUENCE IF NOT EXISTS medico_id_seq;

CREATE UNIQUE INDEX IF NOT EXISTS patients_phone_uidx ON patients(phone) WHERE phone IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS medicos_phone_uidx ON medicos(phone) WHERE phone IS NOT NULL;

CREATE TABLE IF NOT EXISTS studies (
  study_id TEXT PRIMARY KEY,
  patient_id TEXT NOT NULL REFERENCES patients(patient_id),
  "timestamp" TIMESTAMPTZ NOT NULL,
  image_s3_bucket TEXT NOT NULL,
  image_s3_key TEXT NOT NULL,
  source TEXT NOT NULL,
  label TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS predictions (
  prediction_id UUID PRIMARY KEY,
  study_id TEXT NOT NULL REFERENCES studies(study_id),
  model_version TEXT NOT NULL,
  pred_label TEXT NOT NULL,
  prob_sana DOUBLE PRECISION NOT NULL,
  prob_neumonia DOUBLE PRECISION NOT NULL,
  prob_covid DOUBLE PRECISION NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pipeline_events (
  event_id UUID PRIMARY KEY,
  stage TEXT NOT NULL,
  status TEXT NOT NULL,
  message TEXT NOT NULL,
  study_id TEXT,
  payload_ref TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS data_quality_issues (
  issue_id UUID PRIMARY KEY,
  dataset TEXT NOT NULL,
  issue_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  study_id TEXT,
  row_ref TEXT,
  details JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Ingesta CSV (portal + worker)
CREATE TABLE IF NOT EXISTS csv_import_batches (
  batch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  source_filename TEXT,
  row_count INTEGER NOT NULL DEFAULT 0,
  sha256 TEXT,
  quality_summary JSONB,
  ingest_status TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS csv_import_rows (
  row_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_id UUID NOT NULL REFERENCES csv_import_batches(batch_id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  fields JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (batch_id, position)
);

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
