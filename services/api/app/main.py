import os

from fastapi import FastAPI
from minio import Minio
from sqlalchemy import text
from sqlalchemy import create_engine


app = FastAPI(title="Hospital Support API", version="0.1.0")


def _db_engine():
    database_url = os.environ["DATABASE_URL"]
    return create_engine(database_url, pool_pre_ping=True)


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
        engine = _db_engine()
        with engine.connect() as conn:
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

