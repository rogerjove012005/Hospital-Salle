# Observabilidad

Monitorización ligera del stack Docker del hospital (académico).

## Logs de contenedores

En `infra/docker/docker-compose.yml` los servicios críticos usan el driver **`json-file`** con rotación (`max-size: 10m`, `max-file: 3`):

- `api` — peticiones FastAPI y errores de ingesta.
- `csv-ingest-worker` — ciclos de descarga y `POST /imports/csv`.
- `spark-csv-aggregate` — jobs PySpark periódicos.

Consulta local:

```bash
docker compose -f infra/docker/docker-compose.yml logs -f api
docker compose -f infra/docker/docker-compose.yml logs --tail=100 csv-ingest-worker
```

## Salud y métricas de negocio

| Endpoint | Auth | Uso |
|----------|------|-----|
| `GET /health` | No | Liveness del API |
| `GET /health/pipeline` | No | Último agregado Spark |
| `GET /health/observability` | No | Dependencias + contadores CSV/calidad/errores 7d |
| `GET /dashboard/summary` | JWT | KPIs portal |
| `GET /alerts` | JWT admin/medico | Incidencias |

## UI

**Centro de control** (`/analytics.html`) centraliza gráficos y alertas para personal clínico/administrativo.

Para entornos productivos reales se recomendaría Prometheus/Grafana o un APM; aquí se prioriza trazabilidad simple vía logs y eventos en Postgres.
