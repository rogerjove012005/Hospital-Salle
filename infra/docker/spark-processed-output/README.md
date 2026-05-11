# Salida Parquet del job Spark

Montado en el contenedor `spark-csv-aggregate` como `/data/processed/spark`.

Cada ejecución sobrescribe el dataset `csv_row_counts` particionado por `pdate` (derivada del `computed_at` del job).
