import logging
import os
import re
import uuid
from datetime import date
from typing import Annotated, Any, Literal

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .db import engine
from .security import Role, create_access_token, decode_token, hash_password, verify_password


log = logging.getLogger(__name__)

bearer = HTTPBearer(auto_error=False)

_PASSWORD_MIN_LEN = 8
_PASSWORD_MAX_LEN = 128


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    user_id: str
    email: str
    role: Role
    patient_id: str | None = None


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=_PASSWORD_MIN_LEN, max_length=_PASSWORD_MAX_LEN)
    role: Role
    patient_id: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < _PASSWORD_MIN_LEN or len(v) > _PASSWORD_MAX_LEN:
            raise ValueError("Contraseña inválida")
        if not re.search(r"[a-z]", v):
            raise ValueError("La contraseña debe incluir una letra minúscula")
        if not re.search(r"[A-Z]", v):
            raise ValueError("La contraseña debe incluir una letra mayúscula")
        if not re.search(r"\d", v):
            raise ValueError("La contraseña debe incluir un número")
        if not re.search(r"[^A-Za-z0-9]", v):
            raise ValueError("La contraseña debe incluir un símbolo")
        return v

    @field_validator("patient_id")
    @classmethod
    def validate_patient_id(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v2 = v.strip()
        if len(v2) < 3 or len(v2) > 64:
            raise ValueError("patient_id inválido")
        if not re.fullmatch(r"^[A-Za-z0-9][A-Za-z0-9_-]*$", v2):
            raise ValueError("patient_id inválido")
        return v2


class SelfRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=_PASSWORD_MIN_LEN, max_length=_PASSWORD_MAX_LEN)
    role: Literal["paciente", "medico"]

    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    phone: str = Field(min_length=6, max_length=30, pattern=r"^\+?[0-9][0-9\s\-]{5,29}$")
    date_of_birth: date
    sex: Literal["M", "F", "O"]

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        # Keep rules aligned with CreateUserRequest (and avoid pydantic-core unsupported lookaheads)
        if len(v) < _PASSWORD_MIN_LEN or len(v) > _PASSWORD_MAX_LEN:
            raise ValueError("Contraseña inválida")
        if not re.search(r"[a-z]", v):
            raise ValueError("La contraseña debe incluir una letra minúscula")
        if not re.search(r"[A-Z]", v):
            raise ValueError("La contraseña debe incluir una letra mayúscula")
        if not re.search(r"\d", v):
            raise ValueError("La contraseña debe incluir un número")
        if not re.search(r"[^A-Za-z0-9]", v):
            raise ValueError("La contraseña debe incluir un símbolo")
        return v

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_names(cls, v: str) -> str:
        v2 = v.strip()
        if not v2:
            raise ValueError("Campo obligatorio")
        lowered = v2.lower()
        blocked = (
            "nigga",
            "nigger",
            "faggot",
            "retard",
            "bitch",
            "cunt",
            "whore",
            "slut",
        )
        if any(w in lowered for w in blocked):
            raise ValueError("Nombre/apellidos no válidos")
        # Spanish-friendly names: letters (incl. accents), spaces, apostrophes, dots, hyphens
        if not re.fullmatch(r"[A-Za-zÀ-ÿ\u00f1\u00d1\s'.-]+", v2):
            raise ValueError("Nombre/apellidos no válidos")
        return v2

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura")
        return v


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _normalize_phone(phone: str) -> str:
    """Canonical form for storage and uniqueness (spaces/hyphens removed)."""
    return re.sub(r"[\s\-]+", "", phone.strip())


def _register_integrity_error(exc: IntegrityError) -> HTTPException:
    raw = str(getattr(exc, "orig", None) or exc).lower()
    if "app_users" in raw and "email" in raw:
        return HTTPException(status_code=400, detail="Email ya registrado")
    if "patients_phone" in raw or ("patients" in raw and "phone" in raw and "unique" in raw):
        return HTTPException(status_code=400, detail="Teléfono ya registrado")
    if "patients_pkey" in raw or ("patient_id" in raw and "unique" in raw):
        return HTTPException(status_code=409, detail="Conflicto de identificador. Vuelve a intentarlo.")
    log.warning("register_self: unmapped integrity error: %s", exc)
    return HTTPException(
        status_code=400,
        detail="No se pudo completar el registro (datos duplicados o en uso).",
    )


def _age_from_dob(dob: date) -> int:
    today = date.today()
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return max(0, years)


def _next_patient_id(conn) -> str:
    n = conn.execute(text("SELECT nextval('patient_id_seq')")).scalar_one()
    return f"P{int(n):06d}"


def _next_medico_id(conn) -> str:
    n = conn.execute(text("SELECT nextval('medico_id_seq')")).scalar_one()
    return f"M{int(n):06d}"


def ensure_admin_seed() -> None:
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_email or not admin_password:
        return

    with engine().begin() as conn:
        row = conn.execute(
            text("SELECT user_id FROM app_users WHERE email = :email"),
            {"email": _normalize_email(admin_email)},
        ).fetchone()
        if row:
            return

        conn.execute(
            text(
                """
                INSERT INTO app_users(user_id, email, password_hash, role)
                VALUES (:user_id, :email, :password_hash, 'admin')
                """
            ),
            {
                "user_id": str(uuid.uuid4()),
                "email": _normalize_email(admin_email),
                "password_hash": hash_password(admin_password),
            },
        )


def authenticate(email: str, password: str) -> tuple[str, Role, str | None]:
    email_norm = _normalize_email(email)
    with engine().connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT user_id, email, password_hash, role, patient_id
                FROM app_users
                WHERE email = :email
                """
            ),
            {"email": email_norm},
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="No existe una cuenta con ese email")

    password_hash_db: str = row.password_hash
    if not verify_password(password, password_hash_db):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")

    return str(row.user_id), row.role, row.patient_id


def login(req: LoginRequest) -> TokenResponse:
    user_id, role, _patient_id = authenticate(req.email, req.password)
    return TokenResponse(access_token=create_access_token(sub=user_id, role=role))


def _load_user(user_id: str) -> UserOut:
    with engine().connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT user_id, email, role, patient_id
                FROM app_users
                WHERE user_id = :user_id
                """
            ),
            {"user_id": user_id},
        ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid token user")

    return UserOut(
        user_id=str(row.user_id),
        email=row.email,
        role=row.role,
        patient_id=row.patient_id,
    )


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> UserOut:
    if not creds:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    try:
        sub, _role = decode_token(creds.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    return _load_user(sub)


def require_roles(*allowed: Role):
    def _dep(user: Annotated[UserOut, Depends(get_current_user)]) -> UserOut:
        if user.role not in allowed:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return _dep


def create_user(req: CreateUserRequest) -> UserOut:
    user_id = str(uuid.uuid4())
    email_norm = _normalize_email(req.email)
    password_hash = hash_password(req.password)
    with engine().begin() as conn:
        try:
            conn.execute(
                text(
                    """
                    INSERT INTO app_users(user_id, email, password_hash, role, patient_id)
                    VALUES (:user_id, :email, :password_hash, :role, :patient_id)
                    """
                ),
                {
                    "user_id": user_id,
                    "email": email_norm,
                    "password_hash": password_hash,
                    "role": req.role,
                    "patient_id": req.patient_id,
                },
            )
        except IntegrityError as e:
            raise _register_integrity_error(e) from e
        except Exception as e:
            raise HTTPException(status_code=400, detail="User creation failed") from e

    return UserOut(user_id=user_id, email=email_norm, role=req.role, patient_id=req.patient_id)


def _insert_app_user(conn, *, user_id: str, email_norm: str, password: str, role: Role, patient_id: str | None) -> None:
    try:
        conn.execute(
            text(
                """
                INSERT INTO app_users(user_id, email, password_hash, role, patient_id)
                VALUES (:user_id, :email, :password_hash, :role, :patient_id)
                """
            ),
            {
                "user_id": user_id,
                "email": email_norm,
                "password_hash": hash_password(password),
                "role": role,
                "patient_id": patient_id,
            },
        )
    except IntegrityError as e:
        raise _register_integrity_error(e) from e
    except Exception as e:
        raise HTTPException(status_code=400, detail="User creation failed") from e


def register_self(req: SelfRegisterRequest) -> UserOut:
    email_norm = _normalize_email(str(req.email))
    full_name = f"{req.first_name} {req.last_name}".strip()
    age = _age_from_dob(req.date_of_birth)
    phone_norm = _normalize_phone(req.phone)

    try:
        with engine().begin() as conn:
            existing = conn.execute(text("SELECT 1 FROM app_users WHERE email = :email"), {"email": email_norm}).fetchone()
            if existing:
                raise HTTPException(status_code=400, detail="Email already registered")

            phone_row = conn.execute(
                text(
                    """
                    SELECT patient_id FROM patients
                    WHERE regexp_replace(
                        regexp_replace(trim(coalesce(phone, '')), '[[:space:]]+', '', 'g'),
                        '-',
                        '',
                        'g'
                    ) = :phone
                    """
                ),
                {"phone": phone_norm},
            ).fetchone()
            if phone_row:
                raise HTTPException(status_code=400, detail="Teléfono ya registrado")

            if req.role == "paciente":
                patient_id = _next_patient_id(conn)
                conn.execute(
                    text(
                        """
                        INSERT INTO patients(patient_id, age, sex, full_name, phone, date_of_birth)
                        VALUES (:patient_id, :age, :sex, :full_name, :phone, :dob)
                        """
                    ),
                    {
                        "patient_id": patient_id,
                        "age": age,
                        "sex": req.sex,
                        "full_name": full_name,
                        "phone": phone_norm,
                        "dob": req.date_of_birth,
                    },
                )

                user_id = str(uuid.uuid4())
                _insert_app_user(
                    conn,
                    user_id=user_id,
                    email_norm=email_norm,
                    password=req.password,
                    role="paciente",
                    patient_id=patient_id,
                )
                return UserOut(user_id=user_id, email=email_norm, role="paciente", patient_id=patient_id)

            # medico
            medico_ref = _next_medico_id(conn)
            conn.execute(
                text(
                    """
                    INSERT INTO patients(patient_id, age, sex, full_name, phone, date_of_birth)
                    VALUES (:patient_id, :age, :sex, :full_name, :phone, :dob)
                    """
                ),
                {
                    "patient_id": medico_ref,
                    "age": age,
                    "sex": req.sex,
                    "full_name": full_name,
                    "phone": phone_norm,
                    "dob": req.date_of_birth,
                },
            )

            user_id = str(uuid.uuid4())
            _insert_app_user(
                conn,
                user_id=user_id,
                email_norm=email_norm,
                password=req.password,
                role="medico",
                patient_id=None,
            )
            return UserOut(user_id=user_id, email=email_norm, role="medico", patient_id=None)
    except IntegrityError as e:
        raise _register_integrity_error(e) from e


def list_users() -> list[dict[str, Any]]:
    with engine().connect() as conn:
        rows = conn.execute(
            text("SELECT user_id, email, role, patient_id, created_at FROM app_users ORDER BY created_at DESC")
        ).mappings().all()
    return [dict(r) for r in rows]

