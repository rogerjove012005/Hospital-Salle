# Presentación del proyecto

Esquema sugerido para diapositivas (exportar a PDF/PPT según indique el profesor).

## Estructura (12–15 diapositivas)

1. **Portada** — laSalle Health Center, autores, fecha.
2. **Problema** — digitalización hospitalaria, CSV heterogéneos, apoyo RX.
3. **Arquitectura** — Docker Compose: Postgres, API, frontend, MinIO, workers.
4. **Roles y portal** — paciente / médico / admin, capturas del shell UI.
5. **Ingesta automatizada** — worker, mock feed, eventos pipeline.
6. **Calidad de datos** — `data_quality_issues`, ejemplos de alertas.
7. **PySpark** — agregados, Parquet, `csv_spark_run_summary`.
8. **Centro de control** — KPIs, gráficos, informe HTML.
9. **Radiología IA** — clases, métricas, matriz de confusión, ética.
10. **Seguridad** — JWT, RBAC, CORS, sin PII en demos.
11. **Ética y RGPD** — resumen de `docs/ethics/`.
12. **Demo en vivo** — login → import → analytics → RX predict.
13. **Conclusiones y trabajo futuro**.

## Capturas recomendadas

- `landing.html`, `analytics.html`, `radiology.html`, `imports.html` (admin).
- Mailpit para verificación de correo (opcional).

No incluir la memoria Word en este directorio; el `.docx` permanece en la raíz del repositorio según entrega académica.
