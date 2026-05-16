# Prototipo CNN (PyTorch) — guía rápida

Complementa el baseline sklearn empaquetado en la imagen API. Para demostrar **Deep Learning** en evaluación o memoria:

## Requisitos

```bash
cd ml/radiology-classifier
pip install -r requirements-cnn.txt
```

## Entrenar (prototipo)

```bash
python scripts/train_cnn_baseline.py --epochs 5 --out models/cnn_baseline.pt
```

Usa datos en `data/synthetic/` y, si existen, `data/cxr_local/`.

## Evaluar

```bash
python training/cnn_baseline_torch.py --checkpoint models/cnn_baseline.pt
```

## Integración

- El **serving en producción** del portal usa `model_final.pkl` (sklearn) por latencia y reproducibilidad en Docker.
- El CNN queda documentado en ADR `docs/adr/0004-radiology-cnn-prototype-pytorch.md`.

## Criterio académico

Demuestra investigación (arquitectura CNN), entrenamiento PyTorch y comparación cualitativa con el baseline; no es obligatorio sustituir el modelo del API para aprobar la demo.
