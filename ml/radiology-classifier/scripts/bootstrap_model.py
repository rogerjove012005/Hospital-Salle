#!/usr/bin/env python3
"""
Dataset sintético → entrenamiento → evaluación (matriz, ROC, JSON) → nota clínica.
Ejecución esperada desde la carpeta ml/radiology-classifier con PYTHONPATH configurado,
o mediante `python3 scripts/bootstrap_model.py` tras insertar ROOT en sys.path.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _ensure_pkg_root() -> Path:
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def _require_bootstrap_deps() -> None:
    """Fallo temprano con instrucción clara (p. ej. falta seaborn en el venv)."""
    missing: list[str] = []
    for name, mod in (
        ("numpy", "numpy"),
        ("PIL", "PIL"),
        ("sklearn", "sklearn"),
        ("matplotlib", "matplotlib"),
        ("seaborn", "seaborn"),
        ("joblib", "joblib"),
        ("pandas", "pandas"),
    ):
        try:
            __import__(mod)
        except ImportError:
            missing.append(name)
    if missing:
        root = Path(__file__).resolve().parent.parent
        raise SystemExit(
            "Faltan paquetes Python en este entorno: "
            + ", ".join(missing)
            + "\n\nInstálalos desde la carpeta ml/radiology-classifier (macOS: suele no existir `pip`; use python3):\n"
            f"  python3 -m pip install -r {root / 'requirements-sklearn.txt'}\n\n"
            "O bien el requirements completo del módulo (incluye TensorFlow, más pesado):\n"
            f"  python3 -m pip install -r {root / 'requirements.txt'}\n"
        )


def main() -> None:
    _ensure_pkg_root()
    os.environ.setdefault("MPLBACKEND", "Agg")
    _require_bootstrap_deps()

    from configs.config import Config, _radiology_dataset_ready, resolve_radiology_dataset_dir
    from scripts.generate_synthetic_radiology import generate_all
    from training.evaluate import ModelEvaluator
    from training.train import main as train_main
    from inference.clinical_analysis import ClinicalAnalysis

    root = resolve_radiology_dataset_dir()
    print(f"\n→ Dataset resuelto: {root}")
    if root.name == "synthetic":
        if not _radiology_dataset_ready(root):
            generate_all()
    elif not _radiology_dataset_ready(root):
        raise SystemExit(
            "El dataset resuelto no está completo. Ejecute:\n"
            "  python3 scripts/sync_chest_xray_from_downloads.py --source ~/Downloads/chest_xray/train\n"
            "desde ml/radiology-classifier (o ajuste RADIOLOGY_DATA_DIR)."
        )

    model, trainer, X_test, y_test, class_names = train_main()

    model_dir = Path(Config.MODELS_DIR)
    model_dir.mkdir(parents=True, exist_ok=True)
    names_path = model_dir / "class_names.json"
    with names_path.open("w", encoding="utf-8") as f:
        json.dump(class_names, f, ensure_ascii=False, indent=2)

    evaluator = ModelEvaluator(model, class_names)
    evaluator.evaluate(X_test, y_test)
    evaluator.analyze_errors()
    out = str(model_dir)
    evaluator.plot_confusion_matrix(output_dir=out)
    evaluator.plot_roc_curves(output_dir=out)
    evaluator.save_evaluation_report(output_dir=out)

    ClinicalAnalysis(class_names, metrics=evaluator.metrics).generate_clinical_report(output_dir=out)
    print("✓ bootstrap_model.py completado")


if __name__ == "__main__":
    main()
