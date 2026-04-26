import os
from datetime import datetime, timedelta, timezone
from typing import Literal

from jose import JWTError, jwt
from passlib.context import CryptContext


Role = Literal["admin", "medico", "paciente"]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def _jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is required")
    return secret


def create_access_token(*, sub: str, role: Role, expires_in_minutes: int = 60) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_in_minutes)).timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def decode_token(token: str) -> tuple[str, Role]:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except JWTError as e:
        raise ValueError("Invalid token") from e

    sub = payload.get("sub")
    role = payload.get("role")
    if not sub or role not in ("admin", "medico", "paciente"):
        raise ValueError("Invalid token payload")
    return sub, role  # type: ignore[return-value]

