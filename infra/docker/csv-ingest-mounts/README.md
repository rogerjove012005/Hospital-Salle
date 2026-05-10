# Volúmenes de ingesta CSV automatizada

El servicio **`csv-ingest-worker`** monta estos directorios:

| Ruta dentro del contenedor | Uso |
|----------------------------|-----|
| `/data/inbox` | Coloque aquí `*.csv` nuevos desde el host; el worker los sube al API y los mueve tras finalizar |
| `/data/processed` | Archivos ingestados correctamente |
| `/data/failed` | Archivos rechazados o vacíos tras error |
| `/data/state` | `ingest_state.json` (persistencia deduplicación de URLs HTTP) |

Dejar estos directorios en el mismo host que ejecuta Compose; pueden vaciarse con buen criterio en desarrollo para pruebas.
