# Clasificador de radiografías de tórax (triple clase)

Clasificación supervisada en **tres categorías** del encargo: **Sana** (`SANA`), **Neumonía** (`NEUMONIA`), **COVID-19** (`COVID-19`).

## Estado de la implementación (honestidad técnica)

| Aspecto | Implementación en este repo | Relación con el encargo |
|---------|------------------------------|-------------------------|
| **Modelo** | Pipeline **scikit-learn**: `StandardScaler` → `PCA` → `MLPClassifier` sobre imagen aplanada. | Clasificación de imágenes + métricas + matriz de confusión + reflexión clínica. |
| **Deep Learning (CNN)** | **No** está entrenada una CNN en el código actual; está **documentada como evolución** (EfficientNet / ResNet + transfer learning). | El enunciado pide investigar DL; el ADR `docs/adr/0003-radiology-sklearn-baseline.md` justifica el baseline y la migración. |
| **Datos** | **Sintéticos** generados por script (radiografías reales no versionadas). | Cumple privacidad y reproducibilidad académica. |

## Estructura útil

```
ml/radiology-classifier/
├── configs/config.py          # CLASSES, rutas, IMG_SIZE
├── data/                      # synthetic/ (gitignored salvo regeneración)
├── inference/clinical_analysis.py
├── scripts/
│   ├── generate_synthetic_radiology.py
│   └── bootstrap_model.py     # genera datos + train + evaluate + clinical JSON
├── training/
│   ├── preprocess.py
│   ├── train.py
│   ├── evaluate.py
│   └── model.py
└── models/                    # artefactos (gitignored; se crean en Docker o local)
```

## Entorno local (venv recomendado)

```bash
cd ml/radiology-classifier
python3 -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install numpy pillow scikit-learn joblib matplotlib seaborn pandas scipy
export MPLBACKEND=Agg
python scripts/bootstrap_model.py
```

Esto escribe PNG sintéticos, entrena, guarda `models/*` y figuras de evaluación.

## Investigación y decisiones (resumen)

1. **Arquitectura**: PCA reduce dimensionalidad de píxeles; MLP captura no linealidades con coste computacional moderado frente a CNN en CPU.
2. **Preprocesado**: 224×224, gris → tres canales, normalización [0,1]; split estratificado.
3. **Evaluación**: accuracy no es el único foco; se documentan **FN en patologías contagiosas** y lectura de matriz de confusión.
4. **Integración**: artefactos consumidos por la **API** (`/radiology/*`) y UI; build multi-stage en `services/api/Dockerfile`.

## Hoja de ruta hacia Deep Learning

- Dataset público o institucional con gobernanza (CheXpert-like, COVID-19 chest X-ray collections) con splits por hospital.
- **CNN 2D** o **transfer learning** (EfficientNet-B0/B4, ResNet50) con cabeza de 3 logits, fine-tuning parcial.
- **Grad-CAM** o similar para explicabilidad clínica.
- Entrenamiento en GPU (Docker `nvidia-runtime`) y versión de artefacto ONNX/TorchScript.

## Ética y límites

Ver `docs/ethics/radiology-ia-etica.md` y el JSON generado `models/clinical_analysis.json` tras el bootstrap.
