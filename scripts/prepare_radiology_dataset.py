#!/usr/bin/env python3
"""
Prepara el dataset de entrenamiento RX desde datos_prueba/radiografias/chest_xray
y opcionalmente entrena el modelo sklearn empaquetado en la API.

Pasos:
  1. Copia NORMAL/PNEUMONIA (train) → ml/radiology-classifier/data/cxr_local/
  2. Añade COVID-19 (PNG demo + sintéticos para equilibrar)
  3. Sincroniza muestras al portal (galería)
  4. Con --train: bootstrap_model.py y copia artefactos a services/api/app/models/radiology/

Uso (raíz del repo):
  python3 scripts/prepare_radiology_dataset.py
  python3 scripts/prepare_radiology_dataset.py --max-per-class 500 --train
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CHEST_TRAIN = REPO / "datos_prueba" / "radiografias" / "chest_xray" / "train"
ML_PKG = REPO / "ml" / "radiology-classifier"
CXR_LOCAL = ML_PKG / "data" / "cxr_local"
API_MODELS = REPO / "services" / "api" / "app" / "models" / "radiology"
MODEL_ARTIFACTS = (
    "model_final.pkl",
    "class_names.json",
    "evaluation_report.json",
    "confusion_matrix.png",
    "roc_curves.png",
    "clinical_analysis.json",
    "training_info.json",
)


def prepare_cxr_local(max_per_class: int, n_covid_synthetic: int, seed: int) -> None:
    if not (CHEST_TRAIN / "NORMAL").is_dir() or not (CHEST_TRAIN / "PNEUMONIA").is_dir():
        raise SystemExit(
            f"No se encontró el dataset en {CHEST_TRAIN}\n"
            "Coloca Chest X-Ray en datos_prueba/radiografias/chest_xray/train/{{NORMAL,PNEUMONIA}}"
        )

    sync_script = ML_PKG / "scripts" / "sync_chest_xray_from_downloads.py"
    if not sync_script.is_file():
        raise SystemExit(f"Falta {sync_script}")

    cmd = [
        sys.executable,
        str(sync_script),
        "--source",
        str(CHEST_TRAIN),
        "--dest",
        "data/cxr_local",
        "--max-per-class",
        str(max_per_class),
        "--n-covid-synthetic",
        str(n_covid_synthetic),
        "--seed",
        str(seed),
    ]
    print("→ Preparando cxr_local desde Chest X-Ray real…")
    subprocess.run(cmd, cwd=str(ML_PKG), check=True)


def sync_frontend_gallery(per_class: int) -> None:
    gallery_script = REPO / "scripts" / "sync_radiology_samples.py"
    if not gallery_script.is_file():
        return
    print("→ Sincronizando galería del portal…")
    subprocess.run(
        [sys.executable, str(gallery_script), "--per-class", str(min(per_class, 12))],
        cwd=str(REPO),
        check=True,
    )


def _python_for_ml() -> str:
    venv_py = ML_PKG / ".venv" / "bin" / "python"
    if venv_py.is_file():
        return str(venv_py)
    return sys.executable


def train_and_export() -> None:
    bootstrap = ML_PKG / "scripts" / "bootstrap_model.py"
    if not bootstrap.is_file():
        raise SystemExit(f"Falta {bootstrap}")

    py = _python_for_ml()
    print(f"→ Entrenando modelo (bootstrap_model.py) con {py}…")
    import os

    env = os.environ.copy()
    env["MPLBACKEND"] = "Agg"
    subprocess.run([py, str(bootstrap)], cwd=str(ML_PKG), check=True, env=env)

    src = ML_PKG / "models"
    API_MODELS.mkdir(parents=True, exist_ok=True)
    for name in MODEL_ARTIFACTS:
        f = src / name
        if f.is_file():
            shutil.copy2(f, API_MODELS / name)
            print(f"  ✓ {name} → API")
    print(f"✓ Modelo listo en {API_MODELS.relative_to(REPO)}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Dataset RX real + entrenamiento opcional")
    ap.add_argument("--max-per-class", type=int, default=500, help="Imágenes SANA y NEUMONIA desde train/")
    ap.add_argument("--n-covid-synthetic", type=int, default=400, help="Imágenes COVID-19 sintéticas")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--train", action="store_true", help="Entrenar y copiar modelo a la API")
    ap.add_argument("--skip-gallery", action="store_true", help="No actualizar galería frontend")
    args = ap.parse_args()

    prepare_cxr_local(args.max_per_class, args.n_covid_synthetic, args.seed)
    if not args.skip_gallery:
        sync_frontend_gallery(6)

    if args.train:
        train_and_export()
    else:
        print(f"\nDataset en {CXR_LOCAL.relative_to(REPO)}")
        print("Entrena con: python3 scripts/prepare_radiology_dataset.py --train")


if __name__ == "__main__":
    main()
