# Dashboard hospitalario

Capa de visualización y monitorización del proyecto laSalle Health Center.

## Componentes

| Pieza | Ubicación | Función |
|-------|-----------|---------|
| API resumen | `services/api/app/dashboard_ops.py` | KPIs, alertas, informe HTML |
| Frontend | `services/frontend/public/analytics.html` + `analytics.js` | Gráficos Chart.js, alertas, informe |
| Radiología | `radiology.html` | F1 por clase y matriz de confusión |
| Spark stats | `GET /stats/csv-aggregates` | Barras por lote CSV |

## Acceso

- **Admin / médico:** centro de control completo, alertas e informes.
- **Paciente:** resumen reducido (estudios en expediente) sin datos operativos sensibles.

Arranque: `docker compose -f infra/docker/docker-compose.yml up -d` y abrir `http://localhost:3000/analytics.html`.
