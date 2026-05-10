# Ingesta CSV (API)

Endpoints autenticados salvo donde se indique. Formato multipart con campo `file` (CSV UTF-8, límite de tamaño y filas en código).

## Flujo rápido

1. **`POST /imports/csv/preview`** — Parseo y métricas de calidad sin escribir en base de datos.
2. **`POST /imports/csv`** — Crea `csv_import_batches`, inserta filas en `csv_import_rows`, emite eventos (`pipeline_events` etapa `csv_ingestion`) e incidencias de calidad en `data_quality_issues` cuando aplique.

## Dedduplicación y concurrencia

Los lotes se identifican por `sha256` del fichero crudo por usuario. Si el mismo CSV se sube de nuevo, se responde con el lote existente. Si dos peticiones llegan a la vez, la segunda recibe `IntegrityError`, relee el lote existente y no duplica filas ni eventos.

## Archivo en MinIO (opcional)

Tras un import **nuevo** correcto, la API puede guardar una copia del CSV en el bucket `MINIO_CSV_INGEST_BUCKET` (por defecto `hospital-csv-ingest`), clave `ingest/{batch_id}/{nombre}`. Desactivar con `MINIO_CSV_INGEST_DISABLED=1`. La verdad estructural sigue en PostgreSQL.

## Observabilidad

- **`GET /imports/csv/{batch_id}/quality-issues`** — Incidencias asociadas al lote.
- **`GET /admin/imports/pipeline-events`** — Eventos recientes (rol admin); incluye `status=error` si la ingesta falla con excepción interna en `POST /imports/csv`.

## Automatización local

Script en `tools/ingest_csv_folder.sh`: recorre `*.csv` en un directorio y llama a la API con `JWT_TOKEN` en el entorno.
