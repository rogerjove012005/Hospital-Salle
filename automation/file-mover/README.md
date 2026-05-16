# File mover (ingesta CSV)

Script para archivar manualmente CSV que queden en la carpeta **inbox** del worker.

```bash
python automation/file-mover/move_ingest_files.py \
  --inbox infra/docker/csv-ingest-mounts/inbox \
  --processed infra/docker/csv-ingest-mounts/processed \
  --failed infra/docker/csv-ingest-mounts/failed \
  --to processed
```

El worker `csv-ingest-worker` ya mueve ficheros tras `POST /imports/csv`; este util complementa pruebas locales y recuperación de errores.
