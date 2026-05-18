# SDD — Centro de control y operaciones (API + UI)

**Spec-Driven Development** · `dashboard_ops.py`, `analytics.html`

## 1. Descripción funcional

Ofrecer a administradores y médicos un panel con KPIs operativos, alertas consolidadas (pipeline + calidad) y generación de informe HTML del estado del hospital. Los pacientes no ven alertas globales (minimización de datos).

## 2. Inputs y outputs

### Inputs

| Endpoint / fuente | Datos |
|-------------------|-------|
| `pipeline_events` | Últimos eventos de ingesta/Spark |
| `data_quality_issues` | Incidencias por severidad |
| `csv_aggregates`, estudios, pacientes | KPIs |
| JWT con rol | `admin`, `medico`, `paciente` |

### Outputs

| Salida | Formato |
|--------|---------|
| `GET /dashboard/summary` | JSON KPIs + contador alertas |
| `GET /alerts?limit=N` | JSON lista fusionada |
| `GET /reports/hospital` | HTML descargable |
| UI `analytics.html` | Gráficos Chart.js |

## 3. Restricciones

- Roles: alertas e informe global solo `admin` y `medico`.
- Informe generado en cliente (blob) para no exponer JWT en URL.
- Filtrar eventos `ok`/`completed` ruidosos en listado de alertas.
- CORS limitado a origen del frontend (`CORS_ALLOW_ORIGIN`).

## 4. Criterios de aceptación

- [ ] Admin ve KPIs y al menos un gráfico tras importar CSV y ciclo Spark.
- [ ] Incidencia de calidad aparece en `/alerts` tras import con duplicados.
- [ ] Botón «Descargar informe» produce HTML válido con fecha y resumen.
- [ ] Paciente autenticado no recibe alertas operativas en summary.
- [ ] `GET /health/observability` expone contadores sin autenticación (demo).

## 5. Implementación

- API: `services/api/app/dashboard_ops.py`, rutas en `main.py`
- UI: `services/frontend/public/analytics.html`, `analytics.js`
- CLI informe: `automation/reports/generate_hospital_report.py`
