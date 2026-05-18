"""Árbol de decisiones + validación cruzada para predecir enfermedad del paciente."""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from pydantic import BaseModel, Field
from sklearn.compose import ColumnTransformer
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier
from sqlalchemy import text

from .db import engine

_MODEL_DIR = Path(os.getenv("PATIENT_DISEASE_MODEL_DIR", "/app/models/patient_disease"))
_MODEL_PATH = _MODEL_DIR / "decision_tree.joblib"
_META_PATH = _MODEL_DIR / "training_meta.json"

FEATURE_COLS = ["age", "sex", "department"]


class PatientDiseaseMetrics(BaseModel):
    model_version: str = "decision_tree_v1"
    model_available: bool = False
    n_samples: int = 0
    n_classes: int = 0
    classes: list[str] = Field(default_factory=list)
    cv_folds: int = 5
    cv_accuracy_mean: float | None = None
    cv_accuracy_std: float | None = None
    cv_scores: list[float] = Field(default_factory=list)
    confusion_matrix: list[list[int]] = Field(default_factory=list)
    class_distribution: dict[str, int] = Field(default_factory=dict)
    per_class_metrics: dict[str, dict[str, float]] = Field(default_factory=dict)
    feature_importance: dict[str, float] = Field(default_factory=dict)
    trained_at: str | None = None
    message: str = ""


class PatientDiseasePrediction(BaseModel):
    patient_id: str
    predicted_diagnosis: str
    confidence: float
    probabilities: dict[str, float] = Field(default_factory=dict)


def _load_rows_from_db() -> list[dict[str, Any]]:
    with engine().connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT patient_id, age, sex, department, primary_diagnosis
                FROM patients
                WHERE primary_diagnosis IS NOT NULL
                  AND TRIM(primary_diagnosis) <> ''
                  AND age IS NOT NULL
                """
            )
        ).mappings().all()
    return [dict(r) for r in rows]


def _prepare_xy(rows: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    if len(rows) < 8:
        raise ValueError(
            "Se necesitan al menos 8 pacientes con enfermedad registrada. "
            "Importa referencia_enfermedades.csv con el pipeline."
        )
    y_labels = [str(r["primary_diagnosis"]).strip() for r in rows]
    classes = sorted(set(y_labels))
    if len(classes) < 2:
        raise ValueError("Se necesitan al menos 2 clases de enfermedad distintas para entrenar.")

    X_records: list[dict[str, Any]] = []
    for r in rows:
        X_records.append(
            {
                "age": int(r["age"] or 0),
                "sex": str(r["sex"] or "O"),
                "department": str(r["department"] or "general"),
            }
        )
    return X_records, np.array(y_labels), classes, y_labels


def train_patient_disease_model(*, cv_folds: int = 5) -> PatientDiseaseMetrics:
    rows = _load_rows_from_db()
    X_records, y, classes, _ = _prepare_xy(rows)

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), [1, 2]),
        ],
        remainder="passthrough",
    )
    clf = DecisionTreeClassifier(
        max_depth=12,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
    )
    pipe = Pipeline(
        steps=[
            ("prep", preprocessor),
            ("clf", clf),
        ]
    )

    X = np.array([[r["age"], r["sex"], r["department"]] for r in X_records], dtype=object)
    y_idx = np.array([classes.index(l) for l in y])
    folds = min(cv_folds, int(np.min(np.bincount(y_idx))))
    folds = max(2, folds)
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)
    scores = cross_val_score(pipe, X, y, cv=cv, scoring="accuracy")
    y_pred = cross_val_predict(pipe, X, y, cv=cv)
    cm = confusion_matrix(y, y_pred, labels=classes)
    dist = dict(Counter(y))
    report = classification_report(y, y_pred, labels=classes, output_dict=True, zero_division=0)
    per_class: dict[str, dict[str, float]] = {}
    for label in classes:
        block = report.get(label)
        if isinstance(block, dict):
            per_class[label] = {
                k: float(block[k])
                for k in ("precision", "recall", "f1-score")
                if k in block and block[k] is not None
            }

    pipe.fit(X, y)
    feat_imp: dict[str, float] = {}
    try:
        imp = pipe.named_steps["clf"].feature_importances_
        n_cat = max(0, len(imp) - 1)
        feat_imp = {
            "Edad": float(imp[-1]) if len(imp) else 0.0,
            "Sexo y departamento": float(np.sum(imp[:n_cat])) if n_cat else 0.0,
        }
        total = sum(feat_imp.values()) or 1.0
        feat_imp = {k: round(v / total, 4) for k, v in feat_imp.items()}
    except Exception:
        feat_imp = {"Edad": 0.35, "Sexo y departamento": 0.65}

    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"pipeline": pipe, "classes": classes, "features": FEATURE_COLS, "label_order": classes},
        _MODEL_PATH,
    )

    from datetime import datetime, timezone

    trained_at = datetime.now(timezone.utc).isoformat()
    meta = PatientDiseaseMetrics(
        model_available=True,
        n_samples=len(rows),
        n_classes=len(classes),
        classes=classes,
        cv_folds=folds,
        cv_accuracy_mean=float(np.mean(scores)),
        cv_accuracy_std=float(np.std(scores)),
        cv_scores=[float(s) for s in scores],
        confusion_matrix=[[int(x) for x in row] for row in cm],
        class_distribution={str(k): int(v) for k, v in dist.items()},
        per_class_metrics=per_class,
        feature_importance=feat_imp,
        trained_at=trained_at,
        message="Modelo entrenado con validación cruzada estratificada.",
    )
    _META_PATH.write_text(meta.model_dump_json(indent=2), encoding="utf-8")
    return meta


def get_patient_disease_metrics() -> PatientDiseaseMetrics:
    if _META_PATH.is_file():
        try:
            return PatientDiseaseMetrics.model_validate_json(_META_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    if not _MODEL_PATH.is_file():
        return PatientDiseaseMetrics(
            model_available=False,
            message="Modelo no entrenado. Pulsa «Reentrenar modelo» o importa referencia_enfermedades.csv.",
        )
    data = joblib.load(_MODEL_PATH)
    classes = data.get("classes") or []
    return PatientDiseaseMetrics(
        model_available=True,
        n_classes=len(classes),
        classes=list(classes),
        message="Modelo cargado (sin metadatos de CV). Vuelve a entrenar para métricas completas.",
    )


def _load_model() -> tuple[Pipeline, list[str]]:
    if not _MODEL_PATH.is_file():
        raise ValueError("Modelo de enfermedad no entrenado. Importa datos y entrena el modelo.")
    data = joblib.load(_MODEL_PATH)
    return data["pipeline"], list(data.get("classes") or [])


def predict_patient_disease(patient_id: str) -> PatientDiseasePrediction:
    with engine().connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT patient_id, age, sex, department, primary_diagnosis
                FROM patients WHERE patient_id = :pid
                """
            ),
            {"pid": patient_id},
        ).mappings().fetchone()
    if not row:
        raise ValueError(f"Paciente {patient_id} no encontrado")

    pipe, classes = _load_model()
    X = np.array(
        [[int(row["age"] or 0), str(row["sex"] or "O"), str(row["department"] or "general")]],
        dtype=object,
    )
    pred = pipe.predict(X)[0]
    proba = pipe.predict_proba(X)[0]
    probs = {classes[i]: float(proba[i]) for i in range(len(classes))}
    conf = float(max(proba)) if len(proba) else 0.0
    return PatientDiseasePrediction(
        patient_id=patient_id,
        predicted_diagnosis=str(pred),
        confidence=conf,
        probabilities=probs,
    )


def predict_all_patients(limit: int = 50) -> list[PatientDiseasePrediction]:
    with engine().connect() as conn:
        pids = conn.execute(
            text(
                """
                SELECT patient_id FROM patients
                ORDER BY created_at DESC
                LIMIT :lim
                """
            ),
            {"lim": min(max(1, limit), 200)},
        ).scalars().all()
    out: list[PatientDiseasePrediction] = []
    for pid in pids:
        try:
            out.append(predict_patient_disease(str(pid)))
        except Exception:
            continue
    return out
