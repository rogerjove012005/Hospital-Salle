# ADR 003 — Inferencia de radiología embebida en la API Docker

**Estado:** Aceptado  
**Fecha:** 2026-05

## Contexto

El clasificador RX debe integrarse con el portal. Opciones: microservicio ML separado, inferencia solo offline, o modelo dentro del contenedor API.

## Decisión

- **Build multi-stage** en `services/api/Dockerfile`: stage `radiology-build` ejecuta `bootstrap_model.py` y copia `model_final.pkl` + métricas a `/app/models/radiology/`.
- **Inferencia** en runtime con el stack ya presente en API (scikit-learn / pipeline serializado).
- **CNN EfficientNet** documentada y entrenable en `ml/radiology-classifier/` como línea de investigación (`CNN_QUICKSTART.md`).

## Consecuencias

**Ventajas:** Un solo `docker compose up` incluye RX; latencia baja; demo simple para profesores.

**Inconvenientes:** Rebuild de API al cambiar modelo; API más pesada; CNN completa no siempre en producción Docker.

## Alternativas descartadas

| Opción | Motivo |
|--------|--------|
| Servicio TensorFlow Serving | Complejidad operativa excesiva para práctica |
| Solo notebook | No integrable con portal ni pipeline |
| Inferencia en browser | No viable para modelo entrenado en servidor |

## Ética

Toda respuesta de predict incluye contexto de probabilidad; la UI muestra disclaimer. Ver [`docs/ethics/radiology-ia-etica.md`](../ethics/radiology-ia-etica.md).
