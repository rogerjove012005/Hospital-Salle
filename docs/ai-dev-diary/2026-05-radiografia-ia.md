# Diario de desarrollo con IA — módulo de radiografía (mayo 2026)

## Herramienta utilizada

- **Cursor** (editor + agente) como asistente principal para código, Docker, documentación y revisiones de consistencia entre SDD y implementación.

## Justificación breve

- Acelera iteración sobre un monorepo con varios lenguajes (Python ML, FastAPI, Compose, frontend estático).
- Permite mantener trazabilidad entre **especificación** (`docs/specs/`) y **cambios concretos** en `services/` y `ml/`.

## Ejemplos de prompts (representativos)

1. *«Integra el clasificador de radiología en la API con multipart, métricas y roles admin/médico; amplía el Dockerfile con build multi-stage.»*  
   **Resultado:** router `radiology.py`, dependencias, compose con contexto raíz.

2. *«Alinea las tres clases del encargo (Sana, Neumonía, COVID-19) en config, preprocesado y evaluación; corrige análisis de errores que asumía orden fijo de clases.»*  
   **Resultado:** `Config.CLASSES`, `evaluate.py` con `confusion_matrix(..., labels=...)`, FN por nombre de clase.

3. *«Conecta el Chest X-Ray de Downloads (NORMAL/PNEUMONIA) al entrenamiento manteniendo triple clase y documenta el mapeo.»*  
   **Resultado:** `sync_chest_xray_from_downloads.py`, `resolve_radiology_dataset_dir()`, JPEG en `preprocess.py`, SDD actualizada.

4. *«Documenta SDD + ética + ADR sin inventar accuracy clínico; deja claro baseline sklearn vs roadmap CNN.»*  
   **Resultado:** `docs/ethics/radiology-ia-etica.md`, ADR 0003, README ML honesto.

- Estructura de **commits atómicos** y convención **Conventional Commits** en mensajes.
- Detección de **riesgos de integración** (contexto Docker solo `services/api` vs monorepo).

## Donde hubo que corregir / iterar

- **Co-autor automático** en mensajes de commit: había que enmendar con `core.hooksPath` vacío o desactivar la opción en el producto para que el historial refleje solo al autor humano.
- Alineación **README ML** (antes mencionaba EfficientNet) con el **código real** (sklearn): se reescribió para no contradecer el repositorio.

## Reflexión crítica

- La IA reduce tiempo en **boilerplate** (FastAPI, tablas Compose) pero no sustituye el **criterio clínico** ni la lectura del enunciado: hay que revisar siempre claims de «deep learning» vs lo desplegado.
- Riesgo de **sobre-ingeniería**: conviene cortar en MVP documentado y dejar mejoras en ADR / roadmap.

## Impacto estimado (orden de magnitud)

- **Horas ahorradas**: 4–10 h en scaffolding API + Docker + primera pasada de docs frente a solo documentación manual.
- **Calidad**: útil como borrador; la revisión humana de seguridad (JWT, límites de upload) sigue siendo obligatoria.
