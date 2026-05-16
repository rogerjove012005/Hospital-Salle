# Orquestación del pipeline

Flujo automatizado de datos hospitalarios (CSV → API → Postgres → Spark → dashboard).

```mermaid
flowchart LR
  Feed[mock-hospital-feed] --> Worker[csv-ingest-worker]
  Worker --> API[FastAPI /imports/csv]
  API --> PG[(Postgres)]
  Spark[spark-csv-aggregate] --> PG
  API --> Events[pipeline_events]
  Spark --> Events
  PG --> Dash[Centro de control]
```

## Servicios Docker

| Servicio | Script / imagen | Intervalo |
|----------|-----------------|-----------|
| `csv-ingest-worker` | `automated_csv_ingest.py` | `INGEST_POLL_INTERVAL_SECONDS` (90s) |
| `spark-csv-aggregate` | `run_loop.sh` + PySpark | `SPARK_AGGREGATE_INTERVAL_SECONDS` (300s) |

## Eventos

Ambos componentes registran etapas en `pipeline_events` para auditoría y alertas (`GET /alerts`).

Documentación detallada: [`docs/architecture/pipeline-dataflow.md`](../../docs/architecture/pipeline-dataflow.md).
