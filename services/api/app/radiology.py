"""
API de soporte para clasificación de radiografía (triple clase académica).
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel, Field

from .auth import UserOut, require_roles

MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "radiology"
DISCLAIMER = (
    "Resultado sólo orientativo · modelo académico con datos sintéticos · "
    "no constituye diagnóstico médico."
)


class RadiologyMetricsOut(BaseModel):
    available: bool
    class_names: list[str] | None = None
    accuracy: float | None = None
    report_path: str | None = Field(default=None)
    disclaimer: str = DISCLAIMER


class RadiologyPredictOut(BaseModel):
    predicted_class: str
    class_index: int
    probabilities: dict[str, float]
    disclaimer: str = DISCLAIMER


_pipe: Any | None = None
_class_labels: list[str] | None = None


def _load_class_names() -> list[str]:
    p = MODEL_DIR / "class_names.json"
    if not p.is_file():
        raise FileNotFoundError("class_names.json")
    with p.open(encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, list) or not all(isinstance(x, str) for x in raw):
        raise ValueError("class_names inválido")
    return raw


def _load_pipeline():
    global _pipe, _class_labels
    if _pipe is not None and _class_labels is not None:
        return _pipe, _class_labels
    pkl = MODEL_DIR / "model_final.pkl"
    if not pkl.is_file():
        raise FileNotFoundError(str(pkl))
    _pipe = joblib.load(pkl)
    _class_labels = _load_class_names()
    return _pipe, _class_labels


def _preprocess_upload(content: bytes, img_size: int = 224) -> np.ndarray:
    img = Image.open(io.BytesIO(content)).convert("L").resize((img_size, img_size))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    stacked = np.stack([arr] * 3, axis=-1)
    return stacked.reshape(1, -1)


router = APIRouter(prefix="/radiology", tags=["radiology"])


@router.get("/metrics", response_model=RadiologyMetricsOut)
def radiology_metrics(_user: UserOut = Depends(require_roles("admin", "medico"))):
    try:
        _load_pipeline()
    except Exception:
        return RadiologyMetricsOut(available=False)

    classes_out = list(_class_labels or [])
    acc: float | None = None
    rp = MODEL_DIR / "evaluation_report.json"
    if rp.is_file():
        with rp.open(encoding="utf-8") as f:
            data = json.load(f)
        a = data.get("accuracy")
        if a is not None:
            acc = float(a)
        cn = data.get("class_names")
        if isinstance(cn, list) and cn:
            classes_out = [str(x) for x in cn]

    return RadiologyMetricsOut(
        available=True,
        class_names=classes_out,
        accuracy=acc,
        report_path="models/radiology/evaluation_report.json" if rp.is_file() else None,
    )


@router.post("/predict", response_model=RadiologyPredictOut)
async def radiology_predict(
    file: UploadFile = File(...),
    _user: UserOut = Depends(require_roles("admin", "medico")),
):
    ct = (file.content_type or "").lower()
    if file.filename:
        suf = file.filename.lower()
        if not (suf.endswith(".png") or suf.endswith(".jpg") or suf.endswith(".jpeg")):
            raise HTTPException(
                status_code=415,
                detail="Use una imagen PNG o JPEG.",
            )
    elif ct not in {"", "image/png", "image/jpeg", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="Tipo de imagen no admitido.")

    try:
        pipe, labels = _load_pipeline()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Modelo radiología no disponible: {exc}") from exc

    content = await file.read()
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Imagen demasiado grande (máx. 8 MB).")

    try:
        x = _preprocess_upload(content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"No se pudo leer la imagen: {exc}") from exc

    proba = pipe.predict_proba(x)[0]
    idx = int(np.argmax(proba))
    pred = labels[idx] if idx < len(labels) else str(idx)
    probs = {labels[i]: float(proba[i]) for i in range(len(labels))}
    return RadiologyPredictOut(
        predicted_class=pred,
        class_index=idx,
        probabilities=probs,
    )
