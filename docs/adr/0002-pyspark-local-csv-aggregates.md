# ADR 0002 — Procesamiento escalable con PySpark (modo local) sobre filas CSV ingestadas

## Estado

Aceptado — proyecto académico laSalle Health Center.

## Contexto

El encargo exige un framework de procesamiento **distribuido o escalable** (Spark / Dask / Beam) que forme parte del **pipeline de datos** (lectura tras ingesta, transformación/análisis y salida consumible). Los CSV importados viven en PostgreSQL (`csv_import_rows`).

## Decisión

Usar **Apache Spark 3.5** en **modo local (`local[*]`)** dentro de un contenedor Docker dedicado, ejecutando un job PySpark que:

1. Lee datos vía **JDBC** desde `csv_import_rows` (subconsulta con columnas mínimas).
2. Calcula agregados **por lote** (`batch_id` → número de filas).
3. Persiste:
   - tabla relacional `csv_spark_batch_row_counts` y fila de resumen `csv_spark_run_summary` (sobrescritura por ejecución para el último snapshot);
   - **Parquet** particionado por fecha bajo un volumen montado (`/data/processed/spark/...`).

## Alternativas consideradas

| Opción | Pros | Contras |
|--------|------|---------|
| **Dask** sobre Pandas/SQLAlchemy | API Python familiar, ligero | Menos alineado con el enunciado cuando se pide explícitamente “Spark/PySpark”; cluster real también requiere setup |
| **Apache Beam** | Portabilidad de runners | Curva de dependencias y Dockerfile más pesada para una demo acotada |
| **Solo SQL en Postgres** | Mínimo código | No cumple el requisito académico de *framework escalable* |
| **Spark cluster multi-nodo** | Máximo realismo | Complejidad infra innecesaria para volumen docente |

## Consecuencias

- El job es **horizontalmente escalable conceptualmente** (mismo código podría apuntar a un cluster Yarn/K8s sustituyendo el master URL); para el alcance actual basta modo local dentro del contenedor.
- Se añade el driver **JDBC PostgreSQL** al classpath de Spark.
- La API expone **`GET /stats/csv-aggregates`** como capa de *servicio* sobre las tablas de salida Spark.

## Referencias

- Especificación funcional: `docs/specs/pyspark-csv-aggregates.md`
- Diagrama de flujo: `docs/architecture/pipeline-dataflow.md`
