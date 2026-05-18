"""Sincroniza referencias de paciente del CSV con la tabla clínica `patients`."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

_REF_KEYS = ("patient_reference", "patient_id", "paciente", "referencia_paciente")
_NAME_KEYS = ("full_name", "nombre", "name", "paciente_nombre")
_AGE_KEYS = ("age", "edad")
_SEX_KEYS = ("sex", "sexo")
_PHONE_KEYS = ("phone", "telefono", "teléfono", "movil", "móvil")
_DOB_KEYS = ("date_of_birth", "fecha_nacimiento", "dob", "nacimiento")


def _norm_key(key: str) -> str:
    return re.sub(r"[\s\-]+", "_", key.strip().lower())


def _column_map(columns: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for col in columns:
        nk = _norm_key(col)
        out[nk] = col
    return out


def _pick(row: dict[str, str], colmap: dict[str, str], keys: tuple[str, ...]) -> str | None:
    for k in keys:
        nk = _norm_key(k)
        src = colmap.get(nk)
        if not src:
            continue
        val = (row.get(src) or "").strip()
        if val:
            return val
    return None


def _parse_age(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        age = int(float(raw.replace(",", ".")))
        return max(0, min(130, age))
    except ValueError:
        return None


def _parse_sex(raw: str | None) -> str:
    if not raw:
        return "O"
    v = raw.strip().upper()[:1]
    return v if v in ("M", "F", "O") else "O"


def _parse_dob(raw: str | None) -> date | None:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            from datetime import datetime

            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _safe_patient_id(ref: str) -> str | None:
    ref = ref.strip()
    if len(ref) < 2 or len(ref) > 64:
        return None
    if re.fullmatch(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$", ref):
        return ref
    return None


def sync_patients_from_csv_rows(
    conn: Connection,
    columns: list[str],
    data_rows: list[dict[str, str]],
) -> int:
    """
    Inserta pacientes que no existan cuando el CSV incluye una referencia clínica.
    Devuelve el número de fichas nuevas creadas.
    """
    if not data_rows:
        return 0

    colmap = _column_map(columns)
    has_ref = any(_norm_key(k) in colmap for k in _REF_KEYS)
    if not has_ref:
        return 0

    created = 0
    seen: set[str] = set()

    for row in data_rows:
        ref = _pick(row, colmap, _REF_KEYS)
        if not ref:
            continue
        pid = _safe_patient_id(ref)
        if not pid or pid in seen:
            continue
        seen.add(pid)

        exists = conn.execute(
            text("SELECT 1 FROM patients WHERE patient_id = :pid"),
            {"pid": pid},
        ).fetchone()
        if exists:
            continue

        full_name = _pick(row, colmap, _NAME_KEYS) or f"Paciente {pid}"
        age = _parse_age(_pick(row, colmap, _AGE_KEYS))
        sex = _parse_sex(_pick(row, colmap, _SEX_KEYS))
        phone = _pick(row, colmap, _PHONE_KEYS)
        dob = _parse_dob(_pick(row, colmap, _DOB_KEYS))

        if age is None and dob:
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            age = max(0, age)

        try:
            conn.execute(
                text(
                    """
                    INSERT INTO patients(patient_id, age, sex, full_name, phone, date_of_birth)
                    VALUES (:patient_id, :age, :sex, :full_name, :phone, :dob)
                    ON CONFLICT (patient_id) DO NOTHING
                    """
                ),
                {
                    "patient_id": pid,
                    "age": age if age is not None else 0,
                    "sex": sex,
                    "full_name": full_name[:200],
                    "phone": phone[:32] if phone else None,
                    "dob": dob,
                },
            )
            created += 1
        except Exception:
            continue

    return created
