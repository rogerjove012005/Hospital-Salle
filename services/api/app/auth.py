import logging
import os
import re
import secrets
import smtplib
import ssl
import uuid
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Annotated, Any, Literal

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
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
    medico_id: str | None = None


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=_PASSWORD_MIN_LEN, max_length=_PASSWORD_MAX_LEN)
    role: Role
    patient_id: str | None = None
    medico_id: str | None = None
    medico_full_name: str | None = None
    medico_phone: str | None = None
    medico_sex: Literal["M", "F", "O"] | None = None
    medico_date_of_birth: date | None = None

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

    @field_validator("medico_id")
    @classmethod
    def validate_medico_id(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v2 = v.strip()
        if len(v2) < 3 or len(v2) > 64:
            raise ValueError("medico_id inválido")
        if not re.fullmatch(r"^[A-Za-z0-9][A-Za-z0-9_-]*$", v2):
            raise ValueError("medico_id inválido")
        return v2

    @field_validator("medico_full_name")
    @classmethod
    def strip_medico_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v2 = v.strip()
        return v2 or None

    @field_validator("medico_phone")
    @classmethod
    def normalize_admin_medico_phone(cls, v: str | None) -> str | None:
        if v is None or not str(v).strip():
            return None
        p = _normalize_phone(str(v))
        if len(p) < 6 or len(p) > 32:
            raise ValueError("medico_phone inválido")
        return p

    @model_validator(mode="after")
    def coherent_role_fk(self) -> "CreateUserRequest":
        if self.role == "admin":
            if self.patient_id is not None or self.medico_id is not None or self.medico_full_name:
                raise ValueError("Cuenta admin: no asociar patient_id ni ficha de médico")
        elif self.role == "paciente":
            if not self.patient_id:
                raise ValueError("Rol paciente: patient_id es obligatorio (paciente existente en BD)")
            if self.medico_id is not None or self.medico_full_name:
                raise ValueError("Rol paciente: no use campos de médico")
        elif self.role == "medico":
            if self.patient_id is not None:
                raise ValueError("Rol médico: no use patient_id")
            if not self.medico_id and not self.medico_full_name:
                raise ValueError("Rol médico: indique medico_id de una ficha existente o medico_full_name para crear ficha")
        return self


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
    if "medicos_phone" in raw or ("medicos" in raw and "phone" in raw and "unique" in raw):
        return HTTPException(status_code=400, detail="Teléfono ya registrado (médicos)")
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
                INSERT INTO app_users(user_id, email, password_hash, role, patient_id, medico_id)
                VALUES (:user_id, :email, :password_hash, 'admin', NULL, NULL)
                """
            ),
            {
                "user_id": str(uuid.uuid4()),
                "email": _normalize_email(admin_email),
                "password_hash": hash_password(admin_password),
            },
        )


def authenticate(email: str, password: str) -> tuple[str, Role, str | None, str | None]:
    email_norm = _normalize_email(email)
    with engine().connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT user_id, email, password_hash, role, patient_id, medico_id
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

    return str(row.user_id), row.role, row.patient_id, row.medico_id


def login(req: LoginRequest) -> TokenResponse:
    user_id, role, _patient_id, _medico_id = authenticate(req.email, req.password)
    return TokenResponse(access_token=create_access_token(sub=user_id, role=role))


def _load_user(user_id: str) -> UserOut:
    with engine().connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT user_id, email, role, patient_id, medico_id
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
        medico_id=row.medico_id,
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
            raise HTTPException(
                status_code=403,
                detail="Permiso denegado: tu rol no puede acceder a este recurso",
            )
        return user

    return _dep


def create_user(req: CreateUserRequest) -> UserOut:
    user_id = str(uuid.uuid4())
    email_norm = _normalize_email(req.email)

    with engine().begin() as conn:
        try:
            if req.role == "medico" and not req.medico_id:
                medico_id = _next_medico_id(conn)
                full_name = (req.medico_full_name or email_norm.split("@", 1)[0]).strip()
                if not full_name:
                    raise HTTPException(status_code=400, detail="medico_full_name inválido")
                conn.execute(
                    text(
                        """
                        INSERT INTO medicos(medico_id, full_name, phone, date_of_birth, sex)
                        VALUES (:medico_id, :full_name, :phone, :dob, :sex)
                        """
                    ),
                    {
                        "medico_id": medico_id,
                        "full_name": full_name,
                        "phone": req.medico_phone,
                        "dob": req.medico_date_of_birth,
                        "sex": req.medico_sex,
                    },
                )
                _insert_app_user(
                    conn,
                    user_id=user_id,
                    email_norm=email_norm,
                    password=req.password,
                    role="medico",
                    patient_id=None,
                    medico_id=medico_id,
                )
                return UserOut(
                    user_id=user_id,
                    email=email_norm,
                    role="medico",
                    patient_id=None,
                    medico_id=medico_id,
                )

            if req.role == "medico" and req.medico_id:
                row = conn.execute(
                    text("SELECT medico_id FROM medicos WHERE medico_id = :m"),
                    {"m": req.medico_id},
                ).fetchone()
                if not row:
                    raise HTTPException(status_code=400, detail="medico_id no existe en la base de datos")
                _insert_app_user(
                    conn,
                    user_id=user_id,
                    email_norm=email_norm,
                    password=req.password,
                    role="medico",
                    patient_id=None,
                    medico_id=req.medico_id,
                )
                return UserOut(
                    user_id=user_id,
                    email=email_norm,
                    role="medico",
                    patient_id=None,
                    medico_id=req.medico_id,
                )

            if req.role == "paciente":
                _insert_app_user(
                    conn,
                    user_id=user_id,
                    email_norm=email_norm,
                    password=req.password,
                    role="paciente",
                    patient_id=req.patient_id,
                    medico_id=None,
                )
                return UserOut(
                    user_id=user_id,
                    email=email_norm,
                    role="paciente",
                    patient_id=req.patient_id,
                    medico_id=None,
                )

            _insert_app_user(
                conn,
                user_id=user_id,
                email_norm=email_norm,
                password=req.password,
                role="admin",
                patient_id=None,
                medico_id=None,
            )
            return UserOut(
                user_id=user_id,
                email=email_norm,
                role="admin",
                patient_id=None,
                medico_id=None,
            )
        except HTTPException:
            raise
        except IntegrityError as e:
            raise _register_integrity_error(e) from e
        except Exception as e:
            raise HTTPException(status_code=400, detail="User creation failed") from e


def _insert_app_user(
    conn,
    *,
    user_id: str,
    email_norm: str,
    password: str,
    role: Role,
    patient_id: str | None,
    medico_id: str | None = None,
) -> None:
    try:
        conn.execute(
            text(
                """
                INSERT INTO app_users(user_id, email, password_hash, role, patient_id, medico_id)
                VALUES (:user_id, :email, :password_hash, :role, :patient_id, :medico_id)
                """
            ),
            {
                "user_id": user_id,
                "email": email_norm,
                "password_hash": hash_password(password),
                "role": role,
                "patient_id": patient_id,
                "medico_id": medico_id,
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

            pat_phone = conn.execute(
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
            med_phone = conn.execute(
                text(
                    """
                    SELECT medico_id FROM medicos
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
            if pat_phone or med_phone:
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
                    medico_id=None,
                )
                return UserOut(
                    user_id=user_id,
                    email=email_norm,
                    role="paciente",
                    patient_id=patient_id,
                    medico_id=None,
                )

            medico_id = _next_medico_id(conn)
            conn.execute(
                text(
                    """
                    INSERT INTO medicos(medico_id, full_name, phone, date_of_birth, sex)
                    VALUES (:medico_id, :full_name, :phone, :dob, :sex)
                    """
                ),
                {
                    "medico_id": medico_id,
                    "full_name": full_name,
                    "phone": phone_norm,
                    "dob": req.date_of_birth,
                    "sex": req.sex,
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
                medico_id=medico_id,
            )
            return UserOut(
                user_id=user_id,
                email=email_norm,
                role="medico",
                patient_id=None,
                medico_id=medico_id,
            )
    except IntegrityError as e:
        raise _register_integrity_error(e) from e


def list_users() -> list[dict[str, Any]]:
    with engine().connect() as conn:
        rows = conn.execute(
            text(
                "SELECT user_id, email, role, patient_id, medico_id, created_at FROM app_users ORDER BY created_at DESC"
            )
        ).mappings().all()
    return [dict(r) for r in rows]


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=300)
    new_password: str = Field(min_length=_PASSWORD_MIN_LEN, max_length=_PASSWORD_MAX_LEN)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        # Keep rules aligned with CreateUserRequest/SelfRegisterRequest
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


class ResetPasswordResponse(BaseModel):
    message: str


def _app_base_url() -> str:
    # The frontend is served by nginx on localhost:3000 in docker-compose.
    return os.getenv("APP_BASE_URL", "http://localhost:3000").rstrip("/")


def _running_in_docker() -> bool:
    try:
        return os.path.exists("/.dockerenv")
    except OSError:
        return False


def _resolve_smtp_host() -> str:
    """
    Si SMTP_HOST en el .env va vacío, Docker Compose deja la variable a "" y
    antes se desactivaba el envío. En contenedor usamos 'mailpit' por defecto.
    """
    h = (os.getenv("SMTP_HOST") or "").strip()
    if h:
        return h
    if _running_in_docker():
        return "mailpit"
    return ""


def _resolve_smtp_port() -> int:
    host = _resolve_smtp_host()
    raw = (os.getenv("SMTP_PORT") or "").strip()
    if raw.isdigit():
        port = int(raw)
        # .env a menudo trae 587; Mailpit en docker escucha en 1025
        if host == "mailpit" and port == 587:
            return 1025
        return port
    if host == "mailpit":
        return 1025
    return 587


def _resolve_smtp_starttls() -> bool:
    if _resolve_smtp_host() == "mailpit":
        return False
    return os.getenv("SMTP_USE_STARTTLS", "1").strip().lower() in ("1", "true", "yes")


def _smtp_enabled() -> bool:
    return bool(_resolve_smtp_host())


_SMTP_PLACEHOLDER_FRAGMENTS = ("tu_email", "tu_correo", "your@", "your_email", "ejemplo@")


def _looks_like_placeholder(value: str) -> bool:
    v = (value or "").strip().lower()
    if not v:
        return False
    return any(frag in v for frag in _SMTP_PLACEHOLDER_FRAGMENTS)


def _send_reset_email(*, to_email: str, reset_url: str) -> None:
    """
    Send password reset email via SMTP.
    If SMTP is not configured, raises RuntimeError.
    """
    host = _resolve_smtp_host()
    if not host:
        raise RuntimeError("SMTP_HOST is not configured")

    port = _resolve_smtp_port()
    user = (os.getenv("SMTP_USER") or "").strip()
    # Gmail App Passwords are 16 chars; the UI shows them with spaces (e.g. "abcd efgh ijkl mnop").
    # smtplib needs them without spaces. Strip every whitespace defensively.
    password_raw = os.getenv("SMTP_PASSWORD") or ""
    password = "".join(password_raw.split())
    from_email = (os.getenv("SMTP_FROM") or user or "no-reply@lasalle-health.local").strip()
    from_name = os.getenv("SMTP_FROM_NAME", "laSalle Health Center")
    use_ssl = os.getenv("SMTP_USE_SSL", "0").strip().lower() in ("1", "true", "yes")
    use_starttls = _resolve_smtp_starttls()

    # Fail fast with a clear message if the .env still has the example values.
    if _looks_like_placeholder(user) or _looks_like_placeholder(from_email):
        raise RuntimeError(
            f"SMTP_USER/SMTP_FROM look like placeholders (user={user!r}, from={from_email!r}). "
            "Edita infra/docker/.env con tu correo real y reinicia el contenedor api."
        )

    msg = EmailMessage()
    msg["Subject"] = "Restablecer contraseña — laSalle Health Center"
    msg["From"] = f"{from_name} <{from_email}>"
    # Destinatario: el correo que el usuario pide en recuperar; FROM es solo el remitente (SMTP de la plataforma).
    msg["To"] = to_email
    msg.set_content(
        "\n".join(
            [
                "Hemos recibido una solicitud para restablecer tu contraseña.",
                "",
                "Usa este enlace (un solo uso) para establecer una nueva contraseña:",
                reset_url,
                "",
                "Si no has solicitado este cambio, puedes ignorar este mensaje.",
            ]
        )
    )

    if use_ssl:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host=host, port=port, context=context, timeout=10) as server:
            if user and password:
                server.login(user, password)
            server.send_message(msg)
        return

    with smtplib.SMTP(host=host, port=port, timeout=10) as server:
        server.ehlo()
        if use_starttls:
            context = ssl.create_default_context()
            server.starttls(context=context)
            server.ehlo()
        if user and password:
            server.login(user, password)
        server.send_message(msg)


def request_password_reset(req: ForgotPasswordRequest) -> ForgotPasswordResponse:
    """
    Generates a one-time token and stores it.
    For demo environments, we don't send email; we log the reset URL.
    Always returns OK message to avoid account enumeration.
    """
    email_norm = _normalize_email(str(req.email))
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=int(os.getenv("PASSWORD_RESET_TTL_MINUTES", "30")))

    with engine().begin() as conn:
        row = conn.execute(
            text("SELECT user_id FROM app_users WHERE email = :email"),
            {"email": email_norm},
        ).fetchone()
        if row:
            conn.execute(
                text(
                    """
                    INSERT INTO password_reset_tokens(token, user_id, expires_at)
                    VALUES (:token, :user_id, :expires_at)
                    """
                ),
                {"token": token, "user_id": str(row.user_id), "expires_at": expires_at},
            )

            reset_url = f"{_app_base_url()}/reset-password.html?token={token}"
            if _smtp_enabled():
                try:
                    _send_reset_email(to_email=email_norm, reset_url=reset_url)
                    log.info("PASSWORD RESET email sent: email=%s", email_norm)
                except Exception as e:
                    log.exception("PASSWORD RESET email failed: email=%s err=%s", email_norm, e)
                    # Keep demo log as fallback so the reset can still be completed.
                    log.warning("PASSWORD RESET (demo): email=%s url=%s", email_norm, reset_url)
            else:
                log.warning("PASSWORD RESET (demo): email=%s url=%s", email_norm, reset_url)

    return ForgotPasswordResponse(
        message="Si el correo está registrado, recibirá un enlace para restablecer la contraseña."
    )


def reset_password(req: ResetPasswordRequest) -> ResetPasswordResponse:
    token = req.token.strip()
    now = datetime.now(timezone.utc)

    with engine().begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT token, user_id, expires_at, used_at
                FROM password_reset_tokens
                WHERE token = :token
                """
            ),
            {"token": token},
        ).fetchone()

        if not row:
            raise HTTPException(status_code=400, detail="Token inválido")
        if row.used_at is not None:
            raise HTTPException(status_code=400, detail="Token ya usado")
        if row.expires_at is None or row.expires_at < now:
            raise HTTPException(status_code=400, detail="Token caducado")

        conn.execute(
            text("UPDATE app_users SET password_hash = :ph WHERE user_id = :uid"),
            {"ph": hash_password(req.new_password), "uid": str(row.user_id)},
        )
        conn.execute(
            text("UPDATE password_reset_tokens SET used_at = :now WHERE token = :token"),
            {"now": now, "token": token},
        )

    return ResetPasswordResponse(message="Contraseña actualizada. Ya puede iniciar sesión.")

