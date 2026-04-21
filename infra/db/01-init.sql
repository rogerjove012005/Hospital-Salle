CREATE TABLE IF NOT EXISTS patients (
  patient_id TEXT PRIMARY KEY,
  age INTEGER,
  sex TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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
