"""Altas manuales de pacientes y médicos (portal clínico)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .auth import UserOut, hash_password, validate_academic_email, _normalize_email, _normalize_phone
from .db import engine

Sex = Literal["M", "F", "O"]


class CreatePatientIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    age: int = Field(ge=0, le=130)
    sex: Sex
    phone: str | None = None
    department: str | None = Field(default=None, max_length=80)
    primary_diagnosis: str | None = Field(default=None, max_length=120)
    create_portal_user: bool = False
    email: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("email")
    @classmethod
    def norm_email(cls, v: str | None) -> str | None:
        if v is None or not str(v).strip():
            return None
        return validate_academic_email(v)


class CreateMedicoIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    sex: Sex | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    email: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("email")
    @classmethod
    def norm_email(cls, v: str) -> str:
        return validate_academic_email(v)


class DirectoryCreateOut(BaseModel):
    message: str
    patient_id: str | None = None
    medico_id: str | None = None
    user_id: str | None = None


def _next_patient_id(conn) -> str:
    n = conn.execute(text("SELECT nextval('patient_id_seq')")).scalar_one()
    return f"P{int(n):06d}"


def _next_medico_id(conn) -> str:
    n = conn.execute(text("SELECT nextval('medico_id_seq')")).scalar_one()
    return f"M{int(n):06d}"


def create_patient_record(req: CreatePatientIn, _user: UserOut) -> DirectoryCreateOut:
    phone = _normalize_phone(req.phone) if req.phone else None
    dept = (req.department or "").strip() or None
    diag = (req.primary_diagnosis or "").strip() or None
    user_id: str | None = None

    if req.create_portal_user:
        if not req.email or not req.password:
            raise HTTPException(
                status_code=400,
                detail="Para crear acceso al portal indique email y contraseña.",
            )

    with engine().begin() as conn:
        patient_id = _next_patient_id(conn)
        try:
            conn.execute(
                text(
                    """
                    INSERT INTO patients(
                        patient_id, age, sex, full_name, phone,
                        department, primary_diagnosis
                    )
                    VALUES (
                        :patient_id, :age, :sex, :full_name, :phone,
                        :department, :primary_diagnosis
                    )
                    """
                ),
                {
                    "patient_id": patient_id,
                    "age": req.age,
                    "sex": req.sex,
                    "full_name": req.full_name,
                    "phone": phone,
                    "department": dept,
                    "primary_diagnosis": diag,
                },
            )
        except IntegrityError as e:
            raise HTTPException(status_code=400, detail="Teléfono o paciente duplicado.") from e

        if req.create_portal_user and req.email and req.password:
            email_norm = _normalize_email(req.email)
            existing = conn.execute(
                text("SELECT 1 FROM app_users WHERE email = :email"),
                {"email": email_norm},
            ).fetchone()
            if existing:
                raise HTTPException(status_code=400, detail="Email ya registrado.")
            user_id = str(uuid.uuid4())
            conn.execute(
                text(
                    """
                    INSERT INTO app_users(user_id, email, password_hash, role, patient_id, medico_id)
                    VALUES (:user_id, :email, :password_hash, 'paciente', :patient_id, NULL)
                    """
                ),
                {
                    "user_id": user_id,
                    "email": email_norm,
                    "password_hash": hash_password(req.password),
                    "patient_id": patient_id,
                },
            )

    msg = f"Paciente {patient_id} registrado."
    if user_id:
        msg += " Acceso al portal creado."
    return DirectoryCreateOut(message=msg, patient_id=patient_id, user_id=user_id)


def create_medico_record(req: CreateMedicoIn, _user: UserOut) -> DirectoryCreateOut:
    email_norm = _normalize_email(req.email)
    phone = _normalize_phone(req.phone) if req.phone else None

    with engine().begin() as conn:
        existing = conn.execute(
            text("SELECT 1 FROM app_users WHERE email = :email"),
            {"email": email_norm},
        ).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Email ya registrado.")

        medico_id = _next_medico_id(conn)
        try:
            conn.execute(
                text(
                    """
                    INSERT INTO medicos(medico_id, full_name, phone, date_of_birth, sex)
                    VALUES (:medico_id, :full_name, :phone, :dob, :sex)
                    """
                ),
                {
                    "medico_id": medico_id,
                    "full_name": req.full_name,
                    "phone": phone,
                    "dob": req.date_of_birth,
                    "sex": req.sex,
                },
            )
        except IntegrityError as e:
            raise HTTPException(status_code=400, detail="Teléfono o médico duplicado.") from e

        user_id = str(uuid.uuid4())
        conn.execute(
            text(
                """
                INSERT INTO app_users(user_id, email, password_hash, role, patient_id, medico_id)
                VALUES (:user_id, :email, :password_hash, 'medico', NULL, :medico_id)
                """
            ),
            {
                "user_id": user_id,
                "email": email_norm,
                "password_hash": hash_password(req.password),
                "medico_id": medico_id,
            },
        )

    return DirectoryCreateOut(
        message=f"Médico {medico_id} y usuario {email_norm} creados.",
        medico_id=medico_id,
        user_id=user_id,
    )
