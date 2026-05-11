# Especificación: clasificador radiológico (triple clase)

## Alcance

Módulo académico que distingue tres etiquetas en radiografías de tórax procesadas como imagen en escala de gris: **SANA**, **NEUMONIA**, **COVID-19**. Los datos de entrenamiento por defecto son **sintéticos** (texturas generadas por script), coherentes con un entorno de proyecto sin datos clínicos reales.

## Pipeline ML

1. `scripts/generate_synthetic_radiology.py` crea PNG por clase bajo `ml/radiology-classifier/data/synthetic/`.
2. `scripts/bootstrap_model.py` ejecuta entrenamiento (`training/train.py`), evaluación con matriz de confusión y curvas ROC (`training/evaluate.py`) y genera `clinical_analysis.json` (`inference/clinical_analysis.py`).
3. Artefactos en `ml/radiology-classifier/models/`: `model_final.pkl`, `class_names.json`, `evaluation_report.json`, `confusion_matrix.png`, `roc_curves.png`, `clinical_analysis.json`.

Modelo: **sklearn** `StandardScaler` → `PCA` → `MLPClassifier`.

## API

- `GET /radiology/metrics` — métricas agregadas si existe `evaluation_report.json` (JWT, roles `admin` o `medico`).
- `POST /radiology/predict` — multipart con campo `file` (PNG/JPEG); devuelve clase predicha y probabilidades por etiqueta.

Los artefactos se copian en la imagen Docker de la API en `/app/models/radiology/`.

## Frontend

`/radiology.html`: carga métricas y permite subir una imagen de prueba.

## Uso clínico

Sólo **apoyo a la decisión**; no sustituye lectura por especialista ni protocolo de aislamiento/infección. Ver limitaciones y consideraciones éticas en `clinical_analysis.json`.
