# SDD — Agregaciones PySpark sobre `csv_import_rows`

## Descripción funcional

Tras la **ingesta CSV** persistida en PostgreSQL, un job PySpark ejecutado de forma **periódica** (contenedor Compose) refresca información agregada:

- número de **filas importadas por lote** (`batch_id`);
- **total de filas** y **cantidad de lotes con datos** en el último cálculo;
- escritura opcional **Parquet particionado** para simular capa analítica / “warehouse” ligero.

Este módulo cierra el tramo **procesamiento** del pipeline académico sin sustituir la verdad transaccional de `csv_import_rows`.

## Inputs

| Origen | Formato | Notas |
|--------|---------|--------|
| PostgreSQL `csv_import_rows` | filas `batch_id`, `position` | Join adicional con `csv_import_batches` opcional en evoluciones futuras |

Variables de entorno en el job (véase Compose):

- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `SPARK_PARQUET_OUT` (directorio base Parquet dentro del volumen montado)

## Outputs

| Destino | Contenido |
|---------|-----------|
| Tabla `csv_spark_batch_row_counts` | `batch_id`, `row_count`, `computed_at` (último job sobrescribe mediante `truncate` + insert vía JDBC) |
| Tabla `csv_spark_run_summary` | fila singleton `id=1`: `computed_at`, `total_rows`, `batches_with_rows` |
| Parquet `/data/processed/spark/csv_row_counts/` | Dataset particionado por `pdate` derivada de `computed_at` |
| `pipeline_events` | Tras cada ciclo, el worker inserta `stage=spark_csv_aggregate` (ok / error); visibles en `GET /admin/imports/pipeline-events` |
| Observabilidad HTTP | `GET /health/pipeline` expone último `computed_at`, `total_rows`, `batches_with_rows` sin JWT |

## Restricciones

- PostgreSQL debe ser **alcanzable** desde la red Docker (`postgres:5432`).
- El modo Spark es **`local[*]`** (un nodo proceso); suficiente para el volumen docente del proyecto.
- No se modifica el esquema transaccional de ingesta durante el job (solo tablas de agregado dedicadas).

## Criterios de aceptación

1. Con datos en `csv_import_rows`, un ciclo del contenedor `spark-csv-aggregate` deja filas coherentes en `csv_spark_batch_row_counts` y actualiza `csv_spark_run_summary`.
2. Tras el job, existen ficheros Parquet bajo el volumen configurado.
3. `GET /stats/csv-aggregates` (usuario autenticado) devuelve resumen y top de lotes por volumen de filas.
4. El ADR `docs/adr/0002-pyspark-local-csv-aggregates.md` documenta la elección frente a Dask/Beam.

## Diagrama de contexto

Flujo alto nivel (ingesta → almacén → Spark → API): [`docs/architecture/pipeline-dataflow.md`](../architecture/pipeline-dataflow.md).

