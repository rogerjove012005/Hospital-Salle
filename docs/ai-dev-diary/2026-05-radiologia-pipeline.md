# Diario IA — Radiología y pipeline ML (mayo 2026)

## Objetivo

Cumplir el bloque de **clasificación triple** (Sana / Neumonía / COVID-19) con investigación documentada, evaluación clínica y empaquetado en Docker.

## Herramienta

Cursor — prompts sobre arquitectura EfficientNetB4, scripts de entrenamiento y integración API.

## Prompts representativos

1. *«Genera SPECIFICATIONS.md con SDD: inputs 224×224, tres clases, criterios de aceptación y ética.»*
2. *«Implementa evaluate.py con matriz de confusión, ROC y classification_report exportado a JSON.»*
3. *«Crea bootstrap_model.py para que el Dockerfile de la API copie model_final.pkl sin entrenar en cada build si ya existe.»*

## Aciertos

- Pipeline `run_pipeline.py` ejecutable de extremo a extremo.
- `clinical_analysis.py` enlaza métricas con impacto de falsos negativos.
- `CNN_QUICKSTART.md` como segunda vía de investigación.

## Iteraciones necesarias

- Sincronizar nombres de clases (`COVID-19` vs `COVID_19`) entre entrenamiento y API.
- Reducir tamaño de build Docker (no copiar todo `data/synthetic` a la imagen).
- Aclarar en documentación que el modelo en producción demo puede ser baseline sklearn vs CNN completa.

## Productividad

Estimación: **~50 % menos tiempo** en esqueleto de training/evaluación; el tiempo de entrenamiento GPU sigue siendo el cuello de botella humano.

## Referencias

- [`ml/radiology-classifier/SPECIFICATIONS.md`](../../ml/radiology-classifier/SPECIFICATIONS.md)
- [`docs/specs/clasificador-radiologia-sdd.md`](../specs/clasificador-radiologia-sdd.md)
- [`docs/ethics/radiology-ia-etica.md`](../ethics/radiology-ia-etica.md)
