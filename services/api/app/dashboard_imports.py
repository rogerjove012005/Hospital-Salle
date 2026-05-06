import csv
import hashlib
import io
import json
import re
import uuid
from datetime import datetime
from typing import Any, Mapping

from fastapi import HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .auth import UserOut
from .db import engine

_MAX_CSV_BYTES = 2 * 1024 * 1024
_MAX_ROWS = 2000
_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


class CsvRowOut(BaseModel):
    position: int
    fields: dict[str, Any]


class CsvBatchListItem(BaseModel):
    batch_id: str
    source_filename: str | None
    row_count: int
    sha256: str | None = None
    created_at: datetime | None

    @classmethod
    def from_row(cls, r: Mapping[str, Any]) -> "CsvBatchListItem":
        return cls(
            batch_id=str(r["batch_id"]),
            source_filename=r.get("source_filename"),
            row_count=int(r.get("row_count") or 0),
            sha256=r.get("sha256"),
            created_at=r.get("created_at"),
        )


class CsvBatchDetail(BaseModel):
    batch_id: str
    source_filename: str | None
    row_count: int
    sha256: str | None = None
    created_at: datetime | None
    columns: list[str] = Field(default_factory=list)
    rows: list[CsvRowOut]

    @classmethod
    def build(
        cls,
        batch_row: Mapping[str, Any],
        field_rows: list[Mapping[str, Any]],
        columns: list[str],
    ) -> "CsvBatchDetail":
        rows: list[CsvRowOut] = []
        for fr in field_rows:
            raw = fr["fields"]
            row_dict: dict[str, Any] = dict(raw) if isinstance(raw, dict) else {}
            rows.append(CsvRowOut(position=int(fr["position"]), fields=row_dict))
        return cls(
            batch_id=str(batch_row["batch_id"]),
            source_filename=batch_row.get("source_filename"),
            row_count=int(batch_row.get("row_count") or 0),
            sha256=batch_row.get("sha256"),
            created_at=batch_row.get("created_at"),
            columns=columns,
            rows=rows,
        )


class CsvImportResult(BaseModel):
    batch: CsvBatchListItem
    message: str


def _parse_csv_text(raw: str) -> tuple[list[str], list[dict[str, str]]]:
    stream = io.StringIO(raw)
    first_line = stream.readline()
    if not first_line.strip():
        raise HTTPException(status_code=400, detail="El fichero está vacío")
    stream.seek(0)

    reader = csv.DictReader(stream)
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="No se pudo leer la cabecera del CSV (primera fila)")

    headers = [h.strip() or f"columna_{i + 1}" for i, h in enumerate(reader.fieldnames)]
    seen: dict[str, int] = {}
    uniq: list[str] = []
    for h in headers:
        key = h
        if key in seen:
            seen[key] += 1
            key = f"{h}_{seen[h]}"
        else:
            seen[key] = 0
        uniq.append(key)

    out: list[dict[str, str]] = []
    for row in reader:
        if not any((v or "").strip() for v in row.values()):
            continue
        m: dict[str, str] = {}
        for h, u in zip(reader.fieldnames, uniq):
            m[u] = (row.get(h) or "").strip()
        out.append(m)
        if len(out) > _MAX_ROWS:
            raise HTTPException(
                status_code=400,
                detail=f"El CSV supera el máximo de {_MAX_ROWS} filas de datos (sin contar la cabecera).",
            )
    if not out:
        raise HTTPException(status_code=400, detail="No hay filas de datos después de la cabecera")
    return uniq, out


async def import_csv_file(file: UploadFile, user: UserOut) -> CsvImportResult:
    raw_b = await file.read()
    if not raw_b:
        raise HTTPException(status_code=400, detail="El fichero está vacío")
    if len(raw_b) > _MAX_CSV_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"El fichero supera { _MAX_CSV_BYTES // (1024 * 1024) } MB.",
        )
    try:
        textdata = raw_b.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=400, detail="El CSV debe estar en UTF-8") from e

    _cols, data_rows = _parse_csv_text(textdata)
    fn = (file.filename or "importacion.csv")[:200]
    fn = _SAFE_FILENAME.sub("_", fn) or "importacion.csv"
    sha = hashlib.sha256(raw_b).hexdigest()

    uid = uuid.UUID(user.user_id)
    with engine().begin() as conn:
        existing = conn.execute(
            text(
                """
                SELECT batch_id, source_filename, row_count, sha256, created_at
                FROM csv_import_batches
                WHERE user_id = :uid AND sha256 = :sha
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"uid": str(uid), "sha": sha},
        ).mappings().fetchone()
        if existing:
            item = CsvBatchListItem.from_row(existing)
            return CsvImportResult(
                batch=item,
                message="Este CSV ya fue importado anteriormente. Se devuelve el lote existente.",
            )

        b_row = conn.execute(
            text(
                """
                INSERT INTO csv_import_batches (user_id, source_filename, row_count, sha256)
                VALUES (:uid, :fn, :rc, :sha)
                RETURNING batch_id, source_filename, row_count, sha256, created_at
                """
            ),
            {"uid": str(uid), "fn": fn, "rc": len(data_rows), "sha": sha},
        ).mappings().fetchone()
        assert b_row is not None
        bid = str(b_row["batch_id"])

        for i, row in enumerate(data_rows, start=1):
            conn.execute(
                text(
                    """
                    INSERT INTO csv_import_rows (batch_id, position, fields)
                    VALUES (CAST(:bid AS uuid), :pos, CAST(:fields AS jsonb))
                    """
                ),
                {"bid": bid, "pos": i, "fields": json.dumps(row, ensure_ascii=False)},
            )

    item = CsvBatchListItem.from_row(b_row)
    return CsvImportResult(
        batch=item,
        message=f"Importadas {item.row_count} filas.",
    )


def list_user_csv_imports(
    user: UserOut,
    limit: int = 20,
    offset: int = 0,
) -> list[CsvBatchListItem]:
    lim = min(max(1, limit), 100)
    off = max(0, offset)
    uid = str(uuid.UUID(user.user_id))
    with engine().connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT batch_id, source_filename, row_count, sha256, created_at
                FROM csv_import_batches
                WHERE user_id = :uid
                ORDER BY created_at DESC
                LIMIT :lim
                OFFSET :off
                """
            ),
            {"uid": uid, "lim": lim, "off": off},
        ).mappings().all()
    return [CsvBatchListItem.from_row(r) for r in rows]


def get_csv_batch_detail(
    batch_id: str,
    user: UserOut,
    rows_limit: int = 200,
) -> CsvBatchDetail:
    try:
        bid = str(uuid.UUID(batch_id))
    except ValueError as e:
        raise HTTPException(status_code=400, detail="ID de lote no válido") from e

    lim = min(max(1, rows_limit), 1000)
    uid = str(uuid.UUID(user.user_id))
    with engine().connect() as conn:
        batch = conn.execute(
            text(
                """
                SELECT batch_id, source_filename, row_count, sha256, created_at
                FROM csv_import_batches
                WHERE batch_id = :bid AND user_id = :uid
                """
            ),
            {"bid": bid, "uid": uid},
        ).mappings().fetchone()
        if not batch:
            raise HTTPException(status_code=404, detail="Lote no encontrado")

        frows = conn.execute(
            text(
                """
                SELECT position, fields
                FROM csv_import_rows
                WHERE batch_id = :bid
                ORDER BY position
                LIMIT :lim
                """
            ),
            {"bid": bid, "lim": lim},
        ).mappings().all()

    columns: list[str] = []
    for fr in frows:
        d = fr["fields"]
        rowd = dict(d) if isinstance(d, dict) else {}
        for k in rowd:
            if k not in columns:
                columns.append(k)
    return CsvBatchDetail.build(batch, frows, columns)

