# Clasificador de radiografías de tórax (triple clase)

## Arranque rápido (macOS)

1. **Carpeta correcta:** tiene que existir el fichero `requirements-sklearn.txt` junto a `scripts/`. Compruébalo:
   ```bash
   cd "$(git rev-parse --show-toplevel)/ml/radiology-classifier"
   pwd
   ls -la requirements-sklearn.txt scripts/bootstrap_model.py
   ```
   Si `requirements-sklearn.txt` no existe, actualiza el repo (`git pull`) o copia el fichero desde la última versión del proyecto.

2. **No hagas** `cd ml/radiology-classifier` si el prompt ya termina en `radiology-classifier` (estarías intentando entrar en `.../ml/radiology-classifier/ml/radiology-classifier`, que no existe).

3. Instalación y bootstrap (siempre **desde** `ml/radiology-classifier`):
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   python3 -m pip install -r requirements-sklearn.txt
   export MPLBACKEND=Agg
   python3 scripts/sync_chest_xray_from_downloads.py --source ~/Downloads/chest_xray/train
   python3 scripts/bootstrap_model.py
   ```

Clasificación supervisada en **tres categorías** del encargo: **Sana** (`SANA`), **Neumonía** (`NEUMONIA`), **COVID-19** (`COVID-19`).

## Estado de la implementación (honestidad técnica)

| Aspecto | Implementación en este repo | Relación con el encargo |
|---------|------------------------------|-------------------------|
| **Modelo** | Pipeline **scikit-learn**: `StandardScaler` → `PCA` → `MLPClassifier` sobre imagen aplanada. | Clasificación de imágenes + métricas + matriz de confusión + reflexión clínica. |
| **Deep Learning (CNN)** | **Prototipo PyTorch** (`cnn_baseline_torch.py` + `train_cnn_baseline.py`); la API Docker sigue con el **baseline sklearn** por tamaño y reproducibilidad. | Encargo DL: CNN real entrenable localmente; ver ADR **0004** y hoja de ruta transfer learning en ADR **0003**. |
| **Datos** | **Sintéticos** generados por script (radiografías reales no versionadas). | Cumple privacidad y reproducibilidad académica. |

## Estructura útil

```
ml/radiology-classifier/
├── configs/config.py          # CLASSES, rutas, IMG_SIZE
├── data/                      # synthetic/ (gitignored salvo regeneración)
├── inference/clinical_analysis.py
├── scripts/
│   ├── generate_synthetic_radiology.py
│   ├── sync_chest_xray_from_downloads.py
│   ├── bootstrap_model.py
│   └── train_cnn_baseline.py    # CNN PyTorch (opcional)
├── training/
│   ├── preprocess.py
│   ├── train.py
│   ├── cnn_baseline_torch.py    # red convolucional pequeña
│   ├── evaluate.py
│   └── model.py
└── models/                    # artefactos (gitignored; se crean en Docker o local)
```

## Dataset real Chest X-Ray (NORMAL / PNEUMONIA) + COVID sintético

El Chest X-Ray público más habitual incluye solo **NORMAL** y **PNEUMONIA**. Para cumplir la **triple clase** del encargo:

1. Copiá el dataset (por ejemplo desde `~/Downloads/chest_xray/train`) con el script de sincronización (submuestreo opcional).
2. El script crea `data/cxr_local/` con `SANA` ← NORMAL, `NEUMONIA` ← PNEUMONIA y **`COVID-19`** con imágenes **sintéticas** generadas en el mismo repo.

```bash
# Desde la raíz del repositorio (carpeta que contiene ml/ y services/)
cd "$(git rev-parse --show-toplevel)/ml/radiology-classifier"
python3 scripts/sync_chest_xray_from_downloads.py --source ~/Downloads/chest_xray/train
python3 scripts/bootstrap_model.py
```

Si `data/cxr_local/` está completo, `training/train.py` y `bootstrap_model.py` lo usan automáticamente; si no, se usa `data/synthetic/`. Variable opcional: `RADIOLOGY_DATA_DIR`.

## Entorno local (venv recomendado)

```bash
cd "$(git rev-parse --show-toplevel)/ml/radiology-classifier"
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python3 -m pip install -r requirements-sklearn.txt
export MPLBACKEND=Agg
python3 scripts/bootstrap_model.py
```

En macOS a menudo **no** hay comandos `python` ni `pip` en el PATH: usa **`python3`** y **`python3 -m pip`**. Sin venv: `python3 -m pip install --user -r requirements-sklearn.txt`.

Si aparece `ModuleNotFoundError` (p. ej. `seaborn`), reinstala con `python3 -m pip install -r requirements-sklearn.txt` (con el venv activado). El fichero `requirements.txt` histórico incluye TensorFlow y es opcional para este pipeline sklearn.

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

## Prototipo CNN (PyTorch) — Deep Learning en imágenes

Refuerzo del encargo **sin sustituir** el baseline sklearn embebido en la API:

```bash
cd "$(git rev-parse --show-toplevel)/ml/radiology-classifier"
source .venv/bin/activate   # o crea venv como en «Arranque rápido»
python3 -m pip install -r requirements-cnn.txt
python3 scripts/train_cnn_baseline.py --epochs 12
```

Genera `models/cnn_baseline.pt`, `cnn_evaluation.json` y `cnn_confusion_matrix.png`. Detalle de decisión: `docs/adr/0004-radiology-cnn-prototype-pytorch.md`.
