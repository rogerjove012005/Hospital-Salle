# SDD — Agregación PySpark de filas CSV

**Spec-Driven Development** · Módulo `spark-csv-aggregate`

## 1. Descripción funcional

Periodicamente leer las filas importadas en PostgreSQL, calcular agregaciones (conteos por lote) y persistir resultados para consumo del dashboard y del endpoint de estadísticas. Registrar cada ejecución en `pipeline_events`.

## 2. Inputs y outputs

### Inputs

| Parámetro | Fuente |
|-----------|--------|
| `csv_import_rows` | JDBC PostgreSQL |
| Variables entorno | `POSTGRES_*`, `SPARK_PARQUET_OUT`, `SPARK_AGGREGATE_INTERVAL_SECONDS` |

### Outputs

| Destino | Contenido |
|---------|-----------|
| Tabla `csv_aggregates` | `batch_id`, `row_count`, `aggregated_at` |
| Parquet | `/data/processed/spark/csv_row_counts/` (volumen Docker) |
| `pipeline_events` | `stage=spark_csv_aggregate`, `status=ok\|error` |

## 3. Restricciones

- Motor Spark en modo **`local[*]`** (sin cluster externo en la práctica).
- Driver JDBC PostgreSQL 42.x embebido en imagen.
- Ciclo en bucle vía `run_loop.sh`; intervalo default 300s.
- Sin UI de Spark (`spark.ui.enabled=false`) para reducir recursos.

## 4. Criterios de aceptación

- [ ] Tras importar un CSV, en ≤5 min existe fila en `csv_aggregates` para ese `batch_id`.
- [ ] `GET /health/pipeline` refleja última agregación exitosa.
- [ ] Parquet generado en volumen `spark-processed-output` (host).
- [ ] Error de JDBC inserta evento `spark_csv_aggregate` · `error`.
- [ ] `GET /stats/csv-aggregates` devuelve datos coherentes con Postgres.

## 5. Justificación PySpark

Alternativas consideradas: Pandas puro, Dask, Apache Beam. **PySpark** cumple el requisito explícito de framework distribuido/escalable y permite migrar a cluster cambiando solo el master. Ver ADR-002.

## 6. Implementación

- Script: `pipelines/processing/spark_aggregate.py`
- Loop: `pipelines/processing/run_loop.sh`
- Compose: servicio `spark-csv-aggregate`
