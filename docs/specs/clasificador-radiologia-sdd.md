# SDD — Clasificador de radiografías (resumen)

**Spec-Driven Development** · Módulo `ml/radiology-classifier` + API `/radiology/*`

> Especificación detallada del modelo: [`ml/radiology-classifier/SPECIFICATIONS.md`](../../ml/radiology-classifier/SPECIFICATIONS.md)

## 1. Descripción funcional

Clasificar radiografías de tórax en tres categorías para **soporte al triaje** (no diagnóstico definitivo): **Sana**, **Neumonía**, **COVID-19**.

## 2. Inputs y outputs

| Input | Output |
|-------|--------|
| Imagen PNG/JPEG (multipart) | `predicted_class`, probabilidades por clase |
| — | Métricas: `GET /radiology/metrics` (accuracy, F1, matriz) |
| — | Gráfico: `GET /radiology/charts/confusion-matrix` |

## 3. Restricciones

- Disclaimer visible en UI: herramienta académica, no sustituye al médico.
- Modelo empaquetado en build Docker (`model_final.pkl` + artefactos).
- Dataset de entrenamiento sintético o público; sin PHI real.
- Evaluación obligatoria: matriz de confusión + análisis de falsos negativos (COVID).

## 4. Criterios de aceptación

- [ ] `POST /radiology/predict` responde 200 con imagen de prueba válida.
- [ ] Tres clases en `class_names.json`.
- [ ] Matriz de confusión accesible desde portal médico/admin.
- [ ] Documento de ética RX enlazado desde memoria y portal.
- [ ] Reflexión crítica sobre confusión Neumonía ↔ COVID-19 en `clinical_analysis.json`.

## 5. Integración con infraestructura

- Entrenamiento: pipeline local `python run_pipeline.py`
- Despliegue: stage `radiology-build` en `services/api/Dockerfile`
- Almacenamiento opcional de estudios: MinIO + tabla `studies`
