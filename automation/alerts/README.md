# Alertas operativas

Las alertas del hospital se consolidan en la API y en el **Centro de control** (`/analytics.html`).

## Fuentes

| Origen | Tabla / mecanismo | Ejemplo |
|--------|-------------------|---------|
| Pipeline CSV / Spark | `pipeline_events` | `csv_ingest_worker` · `error` |
| Calidad de datos | `data_quality_issues` | Duplicados, filas inválidas |
| Worker de ingesta | `POST /imports/pipeline-events` | Fallo de subida o ciclo |

## API

- `GET /alerts?limit=25` — solo roles **admin** y **medico** (JWT).
- `GET /dashboard/summary` — KPIs y contador de alertas abiertas.

## Automatización

El worker `pipelines/ingestion/automated_csv_ingest.py` registra eventos ante errores de ingesta.
El job Spark (`pipelines/processing/run_loop.sh`) inserta eventos `spark_csv_aggregate` en Postgres.

Para pruebas manuales:

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/alerts?limit=10" | jq
```
