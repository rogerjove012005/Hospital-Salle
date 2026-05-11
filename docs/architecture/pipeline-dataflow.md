# Flujo de datos (ingesta → almacén → procesamiento → servicio)

Vista de referencia para la memoria técnica y la presentación. Describe el **pipeline cerrado** tras la integración del job PySpark (`feature/pipeline`).

## Diagrama (Mermaid)

```mermaid
flowchart LR
  subgraph ingest["Ingesta"]
    UI["Frontend /imports.html"]
    APIup["POST /imports/csv"]
    WK["csv-ingest-worker"]
    FEED["mock-hospital-feed (CSV estático)"]
  end

  subgraph storage["Almacenamiento"]
    PG[("PostgreSQL\ncsv_import_*")]
    MIN[("MinIO\narchivo raw opcional")]
  end

  subgraph process["Procesamiento escalable"]
    SP["spark-csv-aggregate\nPySpark local[*]"]
    PQ["Parquet particionado\n spark-processed-output/"]
  end

  subgraph service["Servicio / visualización"]
    ST["GET /stats/csv-aggregates"]
    DASH["Cliente autenticado\n(dashboard futuro)"]
  end

  UI --> APIup
  WK --> APIup
  FEED --> WK
  APIup --> PG
  APIup -. copia opcional .-> MIN
  PG --> SP
  SP --> PG
  SP --> PQ
  PG --> ST
  ST --> DASH
```

## Resumen narrativo

1. **Ingesta**: operadores o el worker automatizado envían CSV al API; deduplicación y calidad persisten en PostgreSQL; opcionalmente se archiva el fichero en MinIO.
2. **Almacén**: la verdad tabular vive en Postgres; el almacén de objetos cubre el requisito de **datos no estructurados / copias raw**.
3. **Procesamiento**: el contenedor Spark lee `csv_import_rows` por JDBC, calcula agregados por lote, actualiza las tablas `csv_spark_*` y materializa **Parquet** en volumen (capa analítica simulada).
4. **Servicio**: la API expone `GET /stats/csv-aggregates` para consumo desde el portal o un dashboard; el diagrama deja el nodo de visualización abierto a evolución UI.

## Referencias

- SDD PySpark: [`docs/specs/pyspark-csv-aggregates.md`](../specs/pyspark-csv-aggregates.md)
- ADR: [`docs/adr/0002-pyspark-local-csv-aggregates.md`](../adr/0002-pyspark-local-csv-aggregates.md)
- SDD ingesta automática: [`docs/specs/automated-csv-ingestion.md`](../specs/automated-csv-ingestion.md)
