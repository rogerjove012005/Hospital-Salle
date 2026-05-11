#!/usr/bin/env python3
"""
Dataset sintético → entrenamiento → evaluación (matriz, ROC, JSON) → nota clínica.
Ejecución esperada desde la carpeta ml/radiology-classifier con PYTHONPATH configurado,
o mediante `python scripts/bootstrap_model.py` tras insertar ROOT en sys.path.
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


def main() -> None:
    _ensure_pkg_root()
    os.environ.setdefault("MPLBACKEND", "Agg")

    from configs.config import Config
    from scripts.generate_synthetic_radiology import generate_all
    from training.evaluate import ModelEvaluator
    from training.train import main as train_main
    from inference.clinical_analysis import ClinicalAnalysis

    generate_all()
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
