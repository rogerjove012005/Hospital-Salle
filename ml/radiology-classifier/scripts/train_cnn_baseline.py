#!/usr/bin/env python3
"""
Entrena el prototipo CNN (PyTorch) sobre el mismo dataset que el baseline sklearn.
No sustituye la API por defecto; sirve para memoria / encargo (DL en imágenes).

  cd "$(git rev-parse --show-toplevel)/ml/radiology-classifier"
  python3 -m pip install -r requirements-cnn.txt
  python3 scripts/train_cnn_baseline.py --epochs 12
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _ensure_pkg_root() -> Path:
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def _require_torch() -> None:
    try:
        import torch  # noqa: F401
    except ImportError:
        root = Path(__file__).resolve().parent.parent
        raise SystemExit(
            "Falta PyTorch. Instale:\n"
            f"  python3 -m pip install -r {root / 'requirements-cnn.txt'}\n"
            "Guía oficial (CPU/GPU): https://pytorch.org/get-started/locally/"
        ) from None


def main() -> None:
    _ensure_pkg_root()
    _require_torch()
    import argparse

    from training.cnn_baseline_torch import run_training

    ap = argparse.ArgumentParser(description="Entrenar CNN prototipo (PyTorch)")
    ap.add_argument("--epochs", type=int, default=12)
    ap.add_argument("--batch-size", type=int, default=24)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--max-per-class", type=int, default=800)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    os.environ.setdefault("MPLBACKEND", "Agg")
    run_training(
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        max_per_class=args.max_per_class,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
