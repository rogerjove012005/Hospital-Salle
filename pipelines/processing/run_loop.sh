#!/usr/bin/env bash
set -euo pipefail

INTERVAL="${SPARK_AGGREGATE_INTERVAL_SECONDS:-300}"

PGHOST="${POSTGRES_HOST:-postgres}"
PGPORT="${POSTGRES_PORT:-5432}"
PGUSER="${POSTGRES_USER}"
PGDATABASE="${POSTGRES_DB}"
export PGHOST PGPORT PGUSER PGDATABASE

spark_job() {
  /opt/spark/bin/spark-submit \
    --master 'local[*]' \
    --driver-memory "${SPARK_DRIVER_MEMORY:-512m}" \
    --conf spark.ui.enabled=false \
    /app/spark_aggregate.py
}

pipeline_event() {
  local evt_status="$1"
  local evt_message="$2"
  # Mensajes fijos evitan inyección SQL; permite auditoría desde GET /admin/imports/pipeline-events
  if ! PGPASSWORD="${POSTGRES_PASSWORD}" psql -v ON_ERROR_STOP=1 -q -c "INSERT INTO pipeline_events (event_id, stage, status, message, study_id, payload_ref) VALUES (gen_random_uuid(), 'spark_csv_aggregate', '${evt_status}', '${evt_message}', NULL, NULL);" 2>/dev/null; then
    echo '{"event":"pipeline_event_skip","reason":"psql_insert_failed"}'
  fi
}

echo "{\"event\":\"spark_worker_boot\",\"interval_s\":${INTERVAL}}"
while true; do
  if spark_job; then
    pipeline_event "ok" "Agregaciones PySpark CSV escritas en Postgres y Parquet."
  else
    pipeline_event "error" "Fallo ejecutando spark-submit de agregados CSV."
  fi
  sleep "${INTERVAL}"
done
