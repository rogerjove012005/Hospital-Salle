#!/usr/bin/env python3
"""
Genera radiografías sintéticas (PNG escala gris) por clase para desarrollo académico.
No sustituye datos clínicos reales.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def _base_canvas(h: int, w: int, rng: np.random.Generator) -> np.ndarray:
    """Campo tipo tórax: gradiente medio con ruido bajo."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = h * 0.5, w * 0.45
    d = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2) / (h * 0.55)
    base = 0.55 - 0.18 * np.clip(d, 0, 1)
    noise = rng.normal(0.0, 0.022, size=(h, w)).astype(np.float32)
    return np.clip(base + noise, 0.05, 0.94)


def _sana_patch(h: int, w: int, rng: np.random.Generator) -> np.ndarray:
    img = _base_canvas(h, w, rng)
    img += 0.04 * rng.random((h, w), dtype=np.float32)
    return np.clip(img, 0.0, 1.0)


def _neumonia_patch(h: int, w: int, rng: np.random.Generator) -> np.ndarray:
    img = _base_canvas(h, w, rng)
    # Consolidación basal simulada
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    for _ in range(3):
        cy = rng.uniform(h * 0.52, h * 0.92)
        cx = rng.uniform(w * 0.15, w * 0.55)
        sig = rng.uniform(w * 0.08, w * 0.18)
        blob = np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (sig**2)).astype(np.float32)
        img += 0.12 * blob * rng.uniform(0.6, 1.0)
    img += rng.normal(0.0, 0.035, size=(h, w)).astype(np.float32)
    return np.clip(img, 0.0, 1.0)


def _covid_patch(h: int, w: int, rng: np.random.Generator) -> np.ndarray:
    img = _base_canvas(h, w, rng)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx = w / 2.0
    for side in (-1.0, 1.0):
        off = side * rng.uniform(w * 0.12, w * 0.22)
        sx = rng.uniform(w * 0.12, w * 0.2)
        sy = rng.uniform(h * 0.08, h * 0.16)
        haze = np.exp(-(((xx - cx - off) / sx) ** 2 + ((yy - h * 0.48) / sy) ** 2)).astype(
            np.float32
        )
        img += rng.uniform(0.05, 0.11) * haze
    img += rng.normal(0.0, 0.04, size=(h, w)).astype(np.float32)
    return np.clip(img, 0.0, 1.0)


_PATCH = {"SANA": _sana_patch, "NEUMONIA": _neumonia_patch, "COVID-19": _covid_patch}


def write_synthetic_class(
    out_dir: Path,
    class_name: str,
    n: int,
    *,
    seed: int = 42,
    img_size: int = 224,
    prefix: str = "sample",
) -> Path:
    """Escribe n PNG sintéticos para una sola clase (SANA, NEUMONIA o COVID-19)."""
    if class_name not in _PATCH:
        raise ValueError(f"Clase no soportada: {class_name}")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    fn = _PATCH[class_name]
    for i in range(n):
        arr = fn(img_size, img_size, rng)
        pix = (arr * 255.0).clip(0, 255).astype(np.uint8)
        Image.fromarray(pix, mode="L").save(out_dir / f"{prefix}_{i:04d}.png")
    return out_dir


def generate_all(seed: int = 42, n_per_class: int = 48, img_size: int = 224) -> Path:
    root = Path(__file__).resolve().parent.parent / "data" / "synthetic"
    rng = np.random.default_rng(seed)

    for name, fn in _PATCH.items():
        target = root / name
        target.mkdir(parents=True, exist_ok=True)
        for i in range(n_per_class):
            arr = fn(img_size, img_size, rng)
            pix = (arr * 255.0).clip(0, 255).astype(np.uint8)
            Image.fromarray(pix, mode="L").save(target / f"sample_{i:03d}.png")

    print(f"✓ Sintéticas generadas en {root} ({n_per_class} por clase)")
    return root


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n-per-class", type=int, default=48)
    ap.add_argument("--size", type=int, default=224)
    args = ap.parse_args()
    generate_all(seed=args.seed, n_per_class=args.n_per_class, img_size=args.size)


if __name__ == "__main__":
    main()
