#!/usr/bin/env bash
set -euo pipefail

INTERVAL="${SPARK_AGGREGATE_INTERVAL_SECONDS:-300}"

spark_job() {
  /opt/spark/bin/spark-submit \
    --master 'local[*]' \
    --driver-memory "${SPARK_DRIVER_MEMORY:-512m}" \
    --conf spark.ui.enabled=false \
    /app/spark_aggregate.py
}

echo "{\"event\":\"spark_worker_boot\",\"interval_s\":${INTERVAL}}"
while true; do
  spark_job || echo "{\"event\":\"spark_job_failed\",\"ts\":\"$(date -Iseconds)\"}"
  sleep "${INTERVAL}"
done
