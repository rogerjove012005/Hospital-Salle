# ADR 0004: prototipo CNN (PyTorch) para radiografía, paralelo al baseline sklearn

## Estado

Aceptado (refuerzo del encargo «Deep Learning / redes neuronales en imágenes» sin sustituir el despliegue API actual).

## Contexto

El enunciado pide un **módulo de Deep Learning** para imágenes médicas. El baseline productivo (`ADR 0003`) usa **MLP sobre PCA** por reproducibilidad en CPU y build Docker ligero. Eso no sustituye una **CNN convolucional** en el sentido habitual del curso.

## Decisión

Añadir un **segundo camino opcional**: `training/cnn_baseline_torch.py` + `scripts/train_cnn_baseline.py`, que entrena una **CNN pequeña** (tres bloques conv + BN + cabeza densa) sobre el **mismo árbol de datos** que sklearn (`resolve_radiology_dataset_dir()`).

- **Salidas:** `models/cnn_baseline.pt`, `models/cnn_evaluation.json`, `models/cnn_confusion_matrix.png`.
- **Dependencia:** `requirements-cnn.txt` (solo `torch`); no se mezcla con `requirements-sklearn.txt` para no forzar ~2 GB en quien solo quiere el MLP.
- **API / Docker:** siguen sirviendo el **joblib sklearn** embebido en la imagen; la CNN es **artefacto de investigación y memoria** hasta que se integre un endpoint opcional.

## Consecuencias

- La memoria y la defensa pueden mostrar **dos enfoques**: baseline lineal/MLP y **prototipo convolucional** con matriz de confusión propia.
- Mantenimiento: dos pipelines a actualizar si cambian etiquetas o rutas (comparten `Config.CLASSES` y resolución de dataset).

## Alternativas descartadas por ahora

- Sustituir sklearn en Docker por CNN: aumenta tiempo de build y tamaño de imagen.
- TensorFlow/Keras en el mismo contenedor: ya existe `requirements.txt` histórico pesado; PyTorch se añade de forma **opcional** y acotada.
