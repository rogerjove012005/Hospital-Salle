# Feed HTTP simulado (CSV)

`/export.csv` se sirve vía nginx en el servicio Compose `mock-hospital-feed`.

El worker `csv-ingest-worker` (`CSV_PULL_URLS`) descarga estos datos y llama a `POST /imports/csv`.
