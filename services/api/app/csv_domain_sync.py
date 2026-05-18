"""Sincroniza filas CSV con patients, medicos y app_users."""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .auth import hash_password
from .csv_patient_sync import (
    _AGE_KEYS,
    _DOB_KEYS,
    _NAME_KEYS,
    _PHONE_KEYS,
    _REF_KEYS,
    _SEX_KEYS,
    _column_map,
    _parse_age,
    _parse_dob,
    _parse_sex,
    _pick,
    _safe_patient_id,
)

_DISEASE_KEYS = ("enfermedad", "diagnosis", "primary_diagnosis", "patologia", "patología")
_DEPARTMENT_KEYS = ("department", "departamento", "servicio", "area")
_MEDICO_ID_KEYS = ("medico_id", "id_medico", "doctor_id")
_MEDICO_NAME_KEYS = ("medico_nombre", "medico_full_name", "nombre_medico", "doctor_name")
_MEDICO_EMAIL_KEYS = ("medico_email", "email_medico", "doctor_email")
_USER_EMAIL_KEYS = ("email", "correo", "user_email")
_USER_ROLE_KEYS = ("role", "rol", "user_role")
_USER_PASSWORD_KEYS = ("password", "contraseña", "contrasena")


@dataclass
class DomainSyncStats:
    patients_created: int = 0
    patients_updated: int = 0
    medicos_created: int = 0
    medicos_updated: int = 0
    users_created: int = 0
    users_linked: int = 0


def _norm_key(key: str) -> str:
    return re.sub(r"[\s\-]+", "_", key.strip().lower())


def _normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    p = re.sub(r"[\s\-]+", "", phone.strip())
    return p[:32] if p else None


def _next_patient_id(conn: Connection) -> str:
    n = conn.execute(text("SELECT nextval('patient_id_seq')")).scalar_one()
    return f"P{int(n):06d}"


def _next_medico_id(conn: Connection) -> str:
    n = conn.execute(text("SELECT nextval('medico_id_seq')")).scalar_one()
    return f"M{int(n):06d}"


def _infer_diagnosis(row: dict[str, str], colmap: dict[str, str]) -> str | None:
    d = _pick(row, colmap, _DISEASE_KEYS)
    if d:
        return d.strip()[:120]
    sev = (_pick(row, colmap, ("severity_label", "severidad", "gravedad")) or "").lower()
    dept = (_pick(row, colmap, _DEPARTMENT_KEYS) or "").lower()
    o2_raw = _pick(row, colmap, ("oxygen_sat_pct", "saturacion", "saturación", "spo2"))
    try:
        o2 = float(o2_raw) if o2_raw else None
    except ValueError:
        o2 = None
    if sev == "critical" or (o2 is not None and o2 < 90):
        return "neumonia_grave"
    if "urgenc" in dept or sev == "observation":
        return "patologia_respiratoria"
    if sev == "routine":
        return "control_rutinario"
    if "cardio" in dept:
        return "cardiopatia"
    if "radio" in dept:
        return "revision_diagnostica"
    return None


def sync_domain_from_csv_rows(
    conn: Connection,
    columns: list[str],
    data_rows: list[dict[str, str]],
) -> DomainSyncStats:
    stats = DomainSyncStats()
    if not data_rows:
        return stats

    colmap = _column_map(columns)
    default_pwd = os.getenv("IMPORT_USER_PASSWORD", "ImportCsv1!")
    seen_patients: set[str] = set()
    seen_medicos: set[str] = set()

    for row in data_rows:
        # —— Médico ——
        mid = _pick(row, colmap, _MEDICO_ID_KEYS)
        if mid:
            mid = mid.strip()[:64]
        mname = _pick(row, colmap, _MEDICO_NAME_KEYS)
        if mid and mid not in seen_medicos:
            seen_medicos.add(mid)
            exists_m = conn.execute(
                text("SELECT medico_id FROM medicos WHERE medico_id = :m"),
                {"m": mid},
            ).fetchone()
            if exists_m:
                if mname:
                    conn.execute(
                        text(
                            "UPDATE medicos SET full_name = :fn WHERE medico_id = :m"
                        ),
                        {"fn": mname[:200], "m": mid},
                    )
                    stats.medicos_updated += 1
            else:
                conn.execute(
                    text(
                        """
                        INSERT INTO medicos(medico_id, full_name, phone, date_of_birth, sex)
                        VALUES (:m, :fn, NULL, NULL, 'O')
                        """
                    ),
                    {"m": mid, "fn": (mname or f"Médico {mid}")[:200]},
                )
                stats.medicos_created += 1

        # —— Paciente ——
        ref = _pick(row, colmap, _REF_KEYS)
        pid = _safe_patient_id(ref) if ref else None
        if not pid:
            continue
        if pid in seen_patients:
            continue
        seen_patients.add(pid)

        full_name = _pick(row, colmap, _NAME_KEYS) or f"Paciente {pid}"
        age = _parse_age(_pick(row, colmap, _AGE_KEYS))
        sex = _parse_sex(_pick(row, colmap, _SEX_KEYS))
        phone = _normalize_phone(_pick(row, colmap, _PHONE_KEYS))
        dob = _parse_dob(_pick(row, colmap, _DOB_KEYS))
        if age is None and dob:
            today = date.today()
            age = max(
                0,
                today.year
                - dob.year
                - ((today.month, today.day) < (dob.month, dob.day)),
            )
        dept = _pick(row, colmap, _DEPARTMENT_KEYS)
        diagnosis = _infer_diagnosis(row, colmap)

        exists_p = conn.execute(
            text("SELECT patient_id FROM patients WHERE patient_id = :pid"),
            {"pid": pid},
        ).fetchone()
        if exists_p:
            conn.execute(
                text(
                    """
                    UPDATE patients SET
                      full_name = COALESCE(:fn, full_name),
                      age = COALESCE(:age, age),
                      sex = COALESCE(:sex, sex),
                      phone = COALESCE(:phone, phone),
                      date_of_birth = COALESCE(:dob, date_of_birth),
                      department = COALESCE(:dept, department),
                      primary_diagnosis = COALESCE(:dx, primary_diagnosis)
                    WHERE patient_id = :pid
                    """
                ),
                {
                    "pid": pid,
                    "fn": full_name[:200],
                    "age": age,
                    "sex": sex,
                    "phone": phone,
                    "dob": dob,
                    "dept": dept[:80] if dept else None,
                    "dx": diagnosis,
                },
            )
            stats.patients_updated += 1
        else:
            conn.execute(
                text(
                    """
                    INSERT INTO patients(
                      patient_id, age, sex, full_name, phone, date_of_birth,
                      department, primary_diagnosis
                    )
                    VALUES (:pid, :age, :sex, :fn, :phone, :dob, :dept, :dx)
                    """
                ),
                {
                    "pid": pid,
                    "age": age if age is not None else 0,
                    "sex": sex,
                    "fn": full_name[:200],
                    "phone": phone,
                    "dob": dob,
                    "dept": dept[:80] if dept else None,
                    "dx": diagnosis,
                },
            )
            stats.patients_created += 1

        # —— Usuario portal (opcional) ——
        email = _pick(row, colmap, _USER_EMAIL_KEYS)
        role = (_pick(row, colmap, _USER_ROLE_KEYS) or "").strip().lower()
        pwd = _pick(row, colmap, _USER_PASSWORD_KEYS) or default_pwd
        if not email or role not in ("paciente", "medico", "admin"):
            continue
        email = email.strip().lower()[:254]
        uexists = conn.execute(
            text("SELECT user_id FROM app_users WHERE email = :e"),
            {"e": email},
        ).fetchone()
        if uexists:
            conn.execute(
                text(
                    """
                    UPDATE app_users SET
                      role = :role,
                      patient_id = COALESCE(:pid, patient_id),
                      medico_id = COALESCE(:mid, medico_id)
                    WHERE email = :e
                    """
                ),
                {
                    "e": email,
                    "role": role,
                    "pid": pid if role == "paciente" else None,
                    "mid": mid if role == "medico" else None,
                },
            )
            stats.users_linked += 1
        else:
            conn.execute(
                text(
                    """
                    INSERT INTO app_users(user_id, email, password_hash, role, patient_id, medico_id)
                    VALUES (:uid, :e, :ph, :role, :pid, :mid)
                    """
                ),
                {
                    "uid": str(uuid.uuid4()),
                    "e": email,
                    "ph": hash_password(pwd),
                    "role": role,
                    "pid": pid if role == "paciente" else None,
                    "mid": mid if role == "medico" else None,
                },
            )
            stats.users_created += 1

    return stats
