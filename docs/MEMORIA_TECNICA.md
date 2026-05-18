# Memoria técnica — Sistema Inteligente de Soporte Hospitalario

**laSalle Health Center** · Proyecto académico IA y Big Data  
Este documento en Markdown resume los apartados exigidos en el enunciado. La versión formal puede estar en `Informe_Hospital_Salle.pdf`.

---

## 1. Descripción del problema

### Contexto

Hospital de tamaño medio en transformación digital con grandes volúmenes de datos clínicos y operativos sin herramientas avanzadas de análisis ni automatización.

### Objetivos

- Analizar datos clínicos/operativos (CSV + radiografías).
- Detectar patrones, anomalías y clasificaciones (tres clases en RX).
- Automatizar ingesta, agregación e informes.
- Apoyar la toma de decisiones mediante dashboard y métricas de IA (con supervisión humana).

---

## 2. Datos

### Fuentes

| Fuente | Tipo | Uso |
|--------|------|-----|
| `pipelines/ingestion/samples/export.csv` | Estructurado | Simulación sistema legacy |
| mock-hospital-feed (nginx) | API HTTP simulada | Ingesta periódica |
| `ml/radiology-classifier/data/synthetic/` | Imágenes | Entrenamiento RX académico |
| Datasets públicos (opcional) | RX reales | Investigación (`sync_chest_xray_from_downloads.py`) |

### Limpieza y transformación

- Validación en import CSV: duplicados, campos obligatorios, huella de fila.
- Incidencias en `data_quality_issues`.
- RX: redimensionado 224×224, normalización, augmentation en entrenamiento.
- Spark: agregación por `batch_id` desde `csv_import_rows`.

---

## 3. Arquitectura del sistema

Ver diagrama completo: [`architecture/pipeline-dataflow.md`](architecture/pipeline-dataflow.md).

### Infraestructura Docker

Servicios: `postgres`, `minio`, `api`, `frontend`, `mailpit`, `pgadmin`, `mock-hospital-feed`, `csv-ingest-worker`, `spark-csv-aggregate`.

### Pipeline

Ingesta → PostgreSQL → PySpark → API → Portal (Centro de control + Radiología).

### Relación entre componentes

Documentada en ADRs [`adr/`](adr/) y specs [`specs/`](specs/).

---

## 4. Modelos de Inteligencia Artificial

### Justificación

Clasificación triple de radiografías de tórax (Sana, Neumonía, COVID-19) con CNN / transfer learning (EfficientNetB4) y baseline empaquetado para inferencia en API.

### Entrenamiento

Pipeline: `ml/radiology-classifier/run_pipeline.py` (dataset → preprocess → train → evaluate → clinical_analysis).

### Evaluación

- Accuracy, F1 por clase, matriz de confusión, curvas ROC.
- Análisis de falsos negativos en enfermedades contagiosas (`clinical_analysis.json`).

### Resultados

Artefactos en `ml/radiology-classifier/models/` y copiados en imagen API. Visualización en `/radiology.html`.

---

## 5. Automatizaciones

| Automatización | Mecanismo |
|----------------|-----------|
| Ingesta CSV | Worker cada 90s + carpeta inbox |
| Agregación Spark | Bucle cada 300s |
| Alertas | Eventos + tabla calidad → `/alerts` |
| Informe hospital | `GET /reports/hospital` + script CLI |
| Movimiento ficheros | `automation/file-mover/` |

---

## 6. Integraciones

Flujo: **Feed HTTP → Worker → FastAPI → Postgres → Spark → Dashboard / RX**.  
MinIO para objetos; JWT unifica auth entre portal y workers.

---

## 7. Diario de desarrollo con IA

Entregable completo: [`ai-dev-diary/DIARIO_DESARROLLO_IA.md`](ai-dev-diary/DIARIO_DESARROLLO_IA.md)  
Herramienta principal: **Cursor** (agente + edición asistida).

---

## 8. Justificaciones técnicas

| Decisión | Referencia |
|----------|------------|
| Postgres + MinIO | ADR-001 |
| PySpark local | ADR-002 |
| ML en API Docker | ADR-003 |
| FastAPI + JWT | Estándar REST, roles hospitalarios |
| Frontend estático nginx | Despliegue simple, sin SSR |

---

## 9. Reflexión crítica

### Limitaciones

- Datos CSV y RX mayoritariamente sintéticos o de demo.
- Spark no ejecuta en cluster distribuido real.
- Modelo RX no validado clínicamente ni certificado.
- Sin Prometheus/Grafana (observabilidad básica).

### Mejoras futuras

- Cluster Spark/K8s, Kafka para ingesta.
- Dataset RX real + explicabilidad (Grad-CAM).
- Microservicio ML dedicado y A/B de modelos.

### Aplicación en entorno real

Requeriría DPIA, supervisión médica obligatoria, integración HL7/FHIR y gobernanza de modelos.

---

## 10. Consideraciones éticas y legales

- [`ethics/sistema-hospital-ethica.md`](ethics/sistema-hospital-ethica.md)
- [`ethics/radiology-ia-etica.md`](ethics/radiology-ia-etica.md)

Temas: sesgo, automatización supervisada, minimización de datos, RGPD docente, riesgo de falsos negativos en COVID-19.

---

## 11. Referencias de ejecución

```bash
cd infra/docker && cp .env.example .env && docker compose --env-file .env up --build
```

Portal: http://localhost:3000 · API: http://localhost:8000/docs
