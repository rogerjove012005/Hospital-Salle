# SDD — Ingesta automatizada de CSV

**Spec-Driven Development** · Módulo `csv-ingest-worker` + API `/imports/*`

## 1. Descripción funcional

Simular la llegada periódica de datos desde un sistema hospitalario legacy (exportaciones CSV) e incorporarlos al data lake operativo del hospital sin intervención manual. El worker debe ser idempotente ante reintentos y dejar trazabilidad de errores.

## 2. Inputs y outputs

### Inputs

| Origen | Formato | Ejemplo |
|--------|---------|---------|
| URL HTTP | `text/csv` | `http://mock-hospital-feed/export.csv` |
| Carpeta inbox | `.csv` | `infra/docker/csv-ingest-mounts/inbox/` |
| Credenciales | env | `INGEST_LOGIN_EMAIL`, `INGEST_LOGIN_PASSWORD` |

### Outputs

| Destino | Formato |
|---------|---------|
| API `POST /imports/csv` | JSON con `batch_id`, filas insertadas |
| Carpetas `processed/` / `failed/` | Fichero movido + estado en `ingest_state.json` |
| `POST /imports/pipeline-events` | Evento `csv_ingest_worker` · `ok` \| `error` |
| Logs contenedor | JSON por línea (`ts`, `action`, `status`) |

## 3. Restricciones

- Autenticación JWT obligatoria (usuario admin de ingesta).
- No procesar el mismo fichero/URL dos veces si el hash no cambió (`ingest_state.json`).
- Timeout HTTP configurable (`INGEST_HTTP_TIMEOUT_SECONDS`, default 120s).
- Intervalo de sondeo default 90s (`INGEST_POLL_INTERVAL_SECONDS`).

## 4. Criterios de aceptación

- [ ] Con `docker compose up`, el worker importa `export.csv` del mock feed sin intervención.
- [ ] Un CSV duplicado genera incidencia en `data_quality_issues` o rechazo documentado.
- [ ] Fallo de red registra evento `error` visible en `GET /alerts`.
- [ ] Fichero exitoso aparece en `processed/`; fallido en `failed/`.
- [ ] Admin puede listar lotes vía `GET /admin/imports/batches`.

## 5. Implementación

- Worker: `pipelines/ingestion/automated_csv_ingest.py`
- API: `services/api/app/dashboard_imports.py`
- Compose: servicio `csv-ingest-worker` en `infra/docker/docker-compose.yml`
