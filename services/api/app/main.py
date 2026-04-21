import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from minio import Minio
from sqlalchemy import text

from .auth import (
    CreateUserRequest,
    LoginRequest,
    SelfRegisterRequest,
    TokenResponse,
    UserOut,
    create_user,
    ensure_admin_seed,
    get_current_user,
    register_self,
    list_users,
    login,
    require_roles,
)
from .db import engine, init_auth_schema


app = FastAPI(title="Hospital Support API", version="0.1.0")

_cors = os.getenv("CORS_ALLOW_ORIGIN", "*")
if _cors.strip() == "*":
    _allow_origins = ["*"]
    _allow_origin_regex = None
else:
    # Comma-separated list, e.g. "http://localhost:3000,http://127.0.0.1:3000"
    _allow_origins = [o.strip() for o in _cors.split(",") if o.strip()]
    _allow_origin_regex = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_origin_regex=_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _minio_client() -> Minio:
    endpoint = os.environ["MINIO_ENDPOINT"].replace("http://", "").replace("https://", "")
    access_key = os.environ["MINIO_ACCESS_KEY"]
    secret_key = os.environ["MINIO_SECRET_KEY"]
    secure = os.environ["MINIO_ENDPOINT"].startswith("https://")
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/deps")
def health_deps():
    db_ok = False
    minio_ok = False

    try:
        with engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    try:
        client = _minio_client()
        client.list_buckets()
        minio_ok = True
    except Exception:
        minio_ok = False

    return {"postgres": db_ok, "minio": minio_ok}


@app.on_event("startup")
def _startup():
    init_auth_schema()
    ensure_admin_seed()


@app.post("/auth/login", response_model=TokenResponse)
def auth_login(req: LoginRequest):
    return login(req)


@app.post("/auth/register", response_model=UserOut)
def auth_register(req: SelfRegisterRequest):
    return register_self(req)


@app.get("/auth/me", response_model=UserOut)
def auth_me(user: UserOut = Depends(get_current_user)):
    return user


@app.post("/admin/users", response_model=UserOut)
def admin_create_user(req: CreateUserRequest, _admin: UserOut = Depends(require_roles("admin"))):
    return create_user(req)


@app.get("/admin/users")
def admin_list_users(_admin: UserOut = Depends(require_roles("admin"))):
    return list_users()


@app.get("/patients")
def list_patients(_user: UserOut = Depends(require_roles("admin", "medico"))):
    with engine().connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT patient_id, age, sex, full_name, phone, date_of_birth, created_at
                FROM patients
                ORDER BY created_at DESC
                """
            )
        ).mappings().all()
    return [dict(r) for r in rows]


@app.get("/patients/me")
def get_my_patient(user: UserOut = Depends(require_roles("paciente"))):
    if not user.patient_id:
        return None
    with engine().connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT patient_id, age, sex, full_name, phone, date_of_birth, created_at
                FROM patients
                WHERE patient_id = :pid
                """
            ),
            {"pid": user.patient_id},
        ).mappings().fetchone()
    return dict(row) if row else None


@app.get("/studies")
def list_studies(_user: UserOut = Depends(require_roles("admin", "medico"))):
    with engine().connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT study_id, patient_id, timestamp, image_s3_bucket, image_s3_key, source, label, created_at
                FROM studies
                ORDER BY created_at DESC
                """
            )
        ).mappings().all()
    return [dict(r) for r in rows]


@app.get("/studies/me")
def list_my_studies(user: UserOut = Depends(require_roles("paciente"))):
    if not user.patient_id:
        return []
    with engine().connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT study_id, patient_id, timestamp, image_s3_bucket, image_s3_key, source, label, created_at
                FROM studies
                WHERE patient_id = :pid
                ORDER BY created_at DESC
                """
            ),
            {"pid": user.patient_id},
        ).mappings().all()
    return [dict(r) for r in rows]

