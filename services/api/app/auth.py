import os
import uuid
from typing import Annotated, Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import text

from .db import engine
from .security import Role, create_access_token, decode_token, hash_password, verify_password


bearer = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    user_id: str
    email: str
    role: Role
    patient_id: str | None = None


class CreateUserRequest(BaseModel):
    email: str
    password: str
    role: Role
    patient_id: str | None = None


class RegisterRequest(BaseModel):
    email: str
    password: str
    patient_id: str


def ensure_admin_seed() -> None:
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_email or not admin_password:
        return

    with engine().begin() as conn:
        row = conn.execute(
            text("SELECT user_id FROM app_users WHERE email = :email"),
            {"email": admin_email},
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
                "email": admin_email,
                "password_hash": hash_password(admin_password),
            },
        )


def authenticate(email: str, password: str) -> tuple[str, Role, str | None]:
    with engine().connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT user_id, email, password_hash, role, patient_id
                FROM app_users
                WHERE email = :email
                """
            ),
            {"email": email},
        ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    password_hash_db: str = row.password_hash
    if not verify_password(password, password_hash_db):
        raise HTTPException(status_code=401, detail="Invalid credentials")

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
                    "email": req.email,
                    "password_hash": hash_password(req.password),
                    "role": req.role,
                    "patient_id": req.patient_id,
                },
            )
        except Exception as e:  # unique violation, etc.
            raise HTTPException(status_code=400, detail="User creation failed") from e

    return UserOut(user_id=user_id, email=req.email, role=req.role, patient_id=req.patient_id)


def register_patient(req: RegisterRequest) -> UserOut:
    # Public registration is limited to "paciente" for safety.
    with engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO patients(patient_id)
                VALUES (:patient_id)
                ON CONFLICT (patient_id) DO NOTHING
                """
            ),
            {"patient_id": req.patient_id},
        )

    return create_user(
        CreateUserRequest(email=req.email, password=req.password, role="paciente", patient_id=req.patient_id)
    )


def list_users() -> list[dict[str, Any]]:
    with engine().connect() as conn:
        rows = conn.execute(
            text("SELECT user_id, email, role, patient_id, created_at FROM app_users ORDER BY created_at DESC")
        ).mappings().all()
    return [dict(r) for r in rows]

