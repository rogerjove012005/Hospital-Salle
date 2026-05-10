# SDD — Ingesta CSV automatizada (carpeta + feed HTTP simulado)

## Descripción funcional

Complementar la ingesta manual (API/UI) con un proceso **daemon** que incorpora ficheros CSV al sistema sin intervención humana mediante:

1. **Vigilancia de carpeta** (`CSV_INBOX`): cada ciclo procesa ficheros `.csv`; tras respuesta válida los mueve a `processed/` o `failed/`.
2. **Origen tipo API simulado**: uno o más `GET` HTTP (CSV público tras reverse proxy/nginx) configurados en `CSV_PULL_URLS`; el worker descarga y envía a `POST /imports/csv` con JWT de servicio (`INGEST_LOGIN_EMAIL` / contraseña). El contenido inmutable respecto al ciclo anterior no se vuelve a subir.

## Inputs y outputs esperados

| Input | Output |
|-------|--------|
| Ficheros en `infra/docker/csv-ingest-mounts/inbox/` | Lotes en PostgreSQL igual que ingest manual; archivo movido a `processed/` o `failed/` |
| Respuesta de `CSV_PULL_URLS` (UTF-8, CSV válido) | Mismo comportamiento sin mover ficheros locales |
| Credenciales de login válidas contra `/auth/login` | Token Bearer reutilizado en el ciclo |

## Restricciones técnicas y de negocio

- Respeta mismos límites que la API (`tamaño`, `filas`), roles y política deduplicación por `sha256` por usuario de la cuenta de ingesta.
- No debe volcar secretos distintos a variables de entorno ya previstas (`ADMIN_EMAIL` / `ADMIN_PASSWORD` en desarrollo).
- Persistencia interna sólo como `ingest_state.json` bajo `./csv-ingest-mounts/state` (deduplicación de URLs remotas por hash).

## Observabilidad

- Logs estructurados en JSON por línea en stdout (`event`, `detail`, HTTP status, rutas relativas donde aplique).

## Contenedores Compose

| Servicio | Rol |
|---------|-----|
| `mock-hospital-feed` | nginx + CSV estático (simulación de sistema hospitalario) |
| `csv-ingest-worker` | Python worker descrito arriba |

## Criterios de aceptación

1. Con `docker compose up`, el worker realiza login y al menos una ingesta inicial desde URL por defecto sin error 401/500 reproducible si la API está sana.
2. Copiar un CSV válido a `csv-ingest-mounts/inbox` implica que en ≤ un intervalo de sondeo aparece **un** nuevo lote (o resultado `duplicate_file`) y desaparece de la bandeja.
3. CSV vacíos o errores HTTP 4xx mueven archivo a `failed/` (cuando aplique ingestión por carpeta) y queda traza JSON en logs.
4. Desactivación de ingest simulado: vaciar `CSV_PULL_URLS`, reiniciar el worker; debe seguir operando sólo vigilancia carpeta si hay ficheros.
5. El flujo aparece referenciado en `README.md` y coexiste la especificación de API CSV (`csv-ingest-api.md`).
