# Calidad de datos

Reglas de calidad aplicadas durante la ingesta CSV y expuestas como alertas.

## Tabla `data_quality_issues`

Creada en `infra/db/01-init.sql`. El API (`dashboard_imports.py`) inserta incidencias cuando:

- Filas duplicadas o claves repetidas en un lote.
- Campos obligatorios ausentes o tipos incoherentes.
- Referencias a pacientes/estudios inexistentes (según reglas del importador).

## Consulta

- Incidencias por lote: `GET /admin/imports/batches/{batch_id}/quality-issues`
- Alertas globales: `GET /alerts` (fusiona pipeline + calidad)
- Resumen admin: `GET /admin/imports/quality-summary` (conteos por severidad y tipo)

## Buenas prácticas

1. Revisar el Centro de control tras cada importación masiva.
2. Corregir el CSV en origen antes de reintentar.
3. Documentar en el diario de IA cualquier regla nueva (`docs/ai-dev-diary/`).
