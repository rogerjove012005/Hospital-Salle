#!/usr/bin/env python3
"""
Prepara `data/cxr_local/` para entrenar el clasificador triple a partir del Chest X-Ray
clásico (carpetas NORMAL y PNEUMONIA en train/) más imágenes COVID-19 sintéticas.

El dataset público habitual solo tiene 2 clases; el encargo exige tres, por eso
COVID-19 se completa con el generador sintético del propio proyecto.

Uso típico (desde la raíz del repo o desde ml/radiology-classifier):

  python3 scripts/sync_chest_xray_from_downloads.py \\
    --source ~/Downloads/chest_xray/train

Opciones:
  --dest   relativo al paquete (por defecto data/cxr_local)
  --max-per-class  máximo de imágenes copiadas por SANA y NEUMONIA (submuestreo)
  --n-covid-synthetic  número de PNG sintéticos para COVID-19
"""

from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path


def _ensure_pkg_root() -> Path:
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def _copy_samples(src_dir: Path, dst_dir: Path, max_n: int, seed: int) -> int:
    """Copia hasta max_n imágenes (.jpeg/.jpg/.png) de src_dir a dst_dir."""
    if not src_dir.is_dir():
        raise FileNotFoundError(f"No existe la carpeta de origen: {src_dir}")
    dst_dir.mkdir(parents=True, exist_ok=True)
    files = [
        p
        for p in src_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpeg", ".jpg", ".png"}
    ]
    if not files:
        raise FileNotFoundError(f"No hay imágenes en {src_dir}")
    random.Random(seed).shuffle(files)
    take = files[: max_n if max_n > 0 else len(files)]
    for i, p in enumerate(take):
        suf = p.suffix.lower()
        dest = dst_dir / f"cxr_{i:05d}{suf}"
        shutil.copy2(p, dest)
    return len(take)


def main() -> None:
    _ensure_pkg_root()
    ap = argparse.ArgumentParser(description="Montar data/cxr_local desde Chest X-Ray + COVID sintético")
    ap.add_argument(
        "--source",
        type=Path,
        default=Path.home() / "Downloads" / "chest_xray" / "train",
        help="Carpeta train del dataset (debe contener NORMAL/ y PNEUMONIA/)",
    )
    ap.add_argument(
        "--dest",
        type=Path,
        default=Path("data/cxr_local"),
        help="Destino relativo a ml/radiology-classifier/",
    )
    ap.add_argument("--max-per-class", type=int, default=500, help="Máximo imágenes por SANA y NEUMONIA")
    ap.add_argument("--n-covid-synthetic", type=int, default=400, help="Imágenes sintéticas COVID-19")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    pkg = Path(__file__).resolve().parent.parent
    source = Path(args.source).expanduser()
    dest = pkg / args.dest

    if dest.is_dir():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    n_sana = _copy_samples(source / "NORMAL", dest / "SANA", args.max_per_class, args.seed)
    n_neu = _copy_samples(source / "PNEUMONIA", dest / "NEUMONIA", args.max_per_class, args.seed + 1)

    from scripts.generate_synthetic_radiology import write_synthetic_class

    write_synthetic_class(
        dest / "COVID-19",
        "COVID-19",
        args.n_covid_synthetic,
        seed=args.seed + 2,
        prefix="synth_covid",
    )

    print(f"✓ Dataset preparado en {dest}")
    print(f"  SANA (desde NORMAL): {n_sana} imágenes")
    print(f"  NEUMONIA (desde PNEUMONIA): {n_neu} imágenes")
    print(f"  COVID-19 (sintético): {args.n_covid_synthetic} imágenes")
    print("  Entrene con: cd ml/radiology-classifier && python3 scripts/bootstrap_model.py")


if __name__ == "__main__":
    main()
