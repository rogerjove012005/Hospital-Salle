# Informes automatizados

## Informe operativo HTML

- **API:** `GET /reports/hospital` (admin / medico).
- **UI:** botón «Generar informe HTML» en [Centro de control](/analytics.html).
- **CLI:** `python automation/reports/generate_hospital_report.py -o informe.html`

Variables de entorno opcionales: `API_BASE_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`.

El informe resume pipeline CSV/Spark, métricas agregadas y alertas recientes. Es un artefacto académico sin valor clínico.
