# Documentación del proyecto — laSalle Health Center

Índice de entregables documentales del **Sistema Inteligente de Soporte Hospitalario**.

## Memoria y defensa

| Documento | Descripción |
|-----------|-------------|
| [`MEMORIA_TECNICA.md`](MEMORIA_TECNICA.md) | Esqueleto de memoria técnica (11 apartados del enunciado) |
| [`GUIA_DEMOSTRACION_PROFESORES.md`](GUIA_DEMOSTRACION_PROFESORES.md) | Guía de demo 10–15 min |
| [`slides/presentacion-hospital.html`](slides/presentacion-hospital.html) | Presentación en navegador |
| `Informe_Hospital_Salle.pdf` / `Presentacion_Hospital_Salle.key` | Entregables en raíz del repo (local) |

## Spec-Driven Development (SDD)

| Spec | Módulo |
|------|--------|
| [`specs/ingesta-csv-sdd.md`](specs/ingesta-csv-sdd.md) | Worker CSV + API imports |
| [`specs/agregacion-spark-sdd.md`](specs/agregacion-spark-sdd.md) | PySpark |
| [`specs/centro-control-api-sdd.md`](specs/centro-control-api-sdd.md) | Dashboard y alertas |
| [`specs/clasificador-radiologia-sdd.md`](specs/clasificador-radiologia-sdd.md) | IA RX (resumen) |
| [`../ml/radiology-classifier/SPECIFICATIONS.md`](../ml/radiology-classifier/SPECIFICATIONS.md) | IA RX (detalle) |

## Arquitectura y decisiones

| Documento | Contenido |
|-----------|-----------|
| [`architecture/pipeline-dataflow.md`](architecture/pipeline-dataflow.md) | Flujo end-to-end |
| [`adr/001-almacenamiento-postgres-minio.md`](adr/001-almacenamiento-postgres-minio.md) | ADR almacenamiento |
| [`adr/002-pyspark-modo-local.md`](adr/002-pyspark-modo-local.md) | ADR Spark |
| [`adr/003-inferencia-rx-en-api-docker.md`](adr/003-inferencia-rx-en-api-docker.md) | ADR inferencia ML |

## Desarrollo asistido por IA

| Documento | Contenido |
|-----------|-------------|
| [`ai-dev-diary/README.md`](ai-dev-diary/README.md) | Índice del diario |
| [`ai-dev-diary/DIARIO_DESARROLLO_IA.md`](ai-dev-diary/DIARIO_DESARROLLO_IA.md) | **Entregable principal** del diario |
| [`ai-dev-diary/2026-05-operaciones-dashboard.md`](ai-dev-diary/2026-05-operaciones-dashboard.md) | Entrada: centro de control |
| [`ai-dev-diary/2026-05-radiologia-pipeline.md`](ai-dev-diary/2026-05-radiologia-pipeline.md) | Entrada: módulo RX |

## Ética

| Documento | Alcance |
|-----------|---------|
| [`ethics/sistema-hospital-ethica.md`](ethics/sistema-hospital-ethica.md) | Portal, datos, automatización |
| [`ethics/radiology-ia-etica.md`](ethics/radiology-ia-etica.md) | Clasificador de radiografías |

## Operaciones

- [`../infra/observability/README.md`](../infra/observability/README.md)
- [`../pipelines/orchestration/README.md`](../pipelines/orchestration/README.md)
- [`../pipelines/quality/README.md`](../pipelines/quality/README.md)
