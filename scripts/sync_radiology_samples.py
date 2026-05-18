#!/usr/bin/env python3
"""
Copia radiografías de datos_prueba/radiografias/chest_xray al frontend estático
y genera services/frontend/public/samples/rx/manifest.json para la galería RX.

Uso (desde la raíz del repo):
  python3 scripts/sync_radiology_samples.py
  python3 scripts/sync_radiology_samples.py --per-class 8
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CHEST_TEST = REPO / "datos_prueba" / "radiografias" / "chest_xray" / "test"
DST = REPO / "services" / "frontend" / "public" / "samples" / "rx" / "chest"
MANIFEST = REPO / "services" / "frontend" / "public" / "samples" / "rx" / "manifest.json"
COVID_SRC = REPO / "datos_prueba" / "radiografias" / "radiografia_covid_demo.png"

CLASS_MAP = {
    "NORMAL": ("SANA", "Sana"),
    "PNEUMONIA": ("NEUMONIA", "Neumonía"),
}


def copy_class(folder: str, expected: str, label: str, per_class: int) -> list[dict]:
    src_dir = CHEST_TEST / folder
    if not src_dir.is_dir():
        raise FileNotFoundError(f"No existe {src_dir} — coloca el dataset en datos_prueba/radiografias/chest_xray/test/")
    files = sorted(
        [p for p in src_dir.iterdir() if p.is_file() and p.suffix.lower() in {".jpeg", ".jpg", ".png"}],
        key=lambda p: p.name,
    )
    out: list[dict] = []
    for i, p in enumerate(files[:per_class]):
        ext = ".jpg" if p.suffix.lower() in {".jpg", ".jpeg"} else p.suffix.lower()
        name = f"cxr_{folder.lower()}_{i + 1:02d}{ext}"
        shutil.copy2(p, DST / name)
        out.append(
            {
                "id": name,
                "url": f"/samples/rx/chest/{name}",
                "expected_class": expected,
                "label": label,
                "source": f"chest_xray/test/{folder}/{p.name}",
                "title": f"{label} · caso {i + 1}",
            }
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Sincronizar RX Chest X-Ray al portal")
    ap.add_argument("--per-class", type=int, default=6, help="Imágenes por clase NORMAL y PNEUMONIA")
    args = ap.parse_args()

    DST.mkdir(parents=True, exist_ok=True)
    for old in DST.glob("cxr_*"):
        old.unlink()

    samples: list[dict] = []
    for folder, (expected, label) in CLASS_MAP.items():
        samples.extend(copy_class(folder, expected, label, args.per_class))

    if COVID_SRC.is_file():
        covid_name = "cxr_covid_01.png"
        shutil.copy2(COVID_SRC, DST / covid_name)
        samples.append(
            {
                "id": covid_name,
                "url": f"/samples/rx/chest/{covid_name}",
                "expected_class": "COVID-19",
                "label": "COVID-19",
                "source": "datos_prueba/radiografias/radiografia_covid_demo.png",
                "title": "COVID-19 · referencia demo",
            }
        )

    MANIFEST.write_text(
        json.dumps({"version": 1, "samples": samples}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"OK: {len(samples)} muestras → {DST.relative_to(REPO)}")
    print(f"     manifiesto → {MANIFEST.relative_to(REPO)}")


if __name__ == "__main__":
    main()
