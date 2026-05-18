# Diario IA — Operaciones y dashboard (mayo 2026)

## Objetivo

Completar los entregables parciales del enunciado: visualización, alertas, informes automatizados y monitorización, sin modificar la memoria técnica Word.

## Cambios realizados

### API (`dashboard_ops.py`)

- `GET /dashboard/summary` — KPIs por rol.
- `GET /alerts` — fusiona `pipeline_events` y `data_quality_issues`.
- `GET /reports/hospital` — informe HTML descargable.

### Frontend

- Nueva página **Centro de control** (`analytics.html` + `analytics.js`) con Chart.js.
- Radiología: gráfico F1 y imagen de matriz de confusión.
- Entrada en menú lateral del portal (`portal.js`).

### Automatización

- Worker CSV emite `POST /imports/pipeline-events` en errores.
- Script CLI `automation/reports/generate_hospital_report.py`.

### Documentación

- Ética global, READMEs de observabilidad, calidad, orquestación y dashboard.

## Decisiones de diseño

- **Paciente** ve resumen sin alertas operativas ni informe global (principio de minimización).
- Informe HTML generado en cliente vía blob para incluir JWT sin exponer token en URL.
- Alertas filtran eventos `ok/completed` para reducir ruido.

## Pendiente / límites

- Métricas RX dependen del build Docker del modelo (`radiology-build`).
- Sin Prometheus/Grafana; logs Docker `json-file` como observabilidad base.

## Referencias

- Enunciado práctica hospital · PDF curso.
- [`docs/architecture/pipeline-dataflow.md`](../architecture/pipeline-dataflow.md) (flujo end-to-end)
- [`docs/ai-dev-diary/DIARIO_DESARROLLO_IA.md`](DIARIO_DESARROLLO_IA.md) (diario consolidado)
