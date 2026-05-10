import csv
import hashlib
import io
import json
import logging
import os
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

_log = logging.getLogger(__name__)

_MAX_CSV_BYTES = 2 * 1024 * 1024
_MAX_ROWS = 2000
_MAX_PREVIEW_ROWS = 25
_MAX_DQ_ISSUES_PER_IMPORT = 80
_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


class CsvRowOut(BaseModel):
    position: int
    fields: dict[str, Any]


class QualitySummary(BaseModel):
    """Resumen automático tras parsear filas CSV (sin juzgar negocio clínico)."""

    column_count: int
    row_count: int
    empty_columns: list[str] = Field(default_factory=list)
    rows_with_any_blank_cell: int = 0
    completeness_ratio: float = 1.0
    duplicate_row_groups: int = 0
    duplicate_positions_sample: list[int] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)


class CsvBatchListItem(BaseModel):
    batch_id: str
    source_filename: str | None
    row_count: int
    sha256: str | None = None
    ingest_status: str | None = None
    quality_summary: QualitySummary | None = None
    created_at: datetime | None

    @classmethod
    def from_row(cls, r: Mapping[str, Any]) -> "CsvBatchListItem":
        q = r.get("quality_summary")
        summary: QualitySummary | None = None
        if isinstance(q, dict):
            try:
                summary = QualitySummary.model_validate(q)
            except Exception:
                summary = None
        return cls(
            batch_id=str(r["batch_id"]),
            source_filename=r.get("source_filename"),
            row_count=int(r.get("row_count") or 0),
            sha256=r.get("sha256"),
            ingest_status=r.get("ingest_status"),
            quality_summary=summary,
            created_at=r.get("created_at"),
        )


class CsvBatchDetail(BaseModel):
    batch_id: str
    source_filename: str | None
    row_count: int
    sha256: str | None = None
    ingest_status: str | None = None
    quality_summary: QualitySummary | None = None
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
        q = batch_row.get("quality_summary")
        summary: QualitySummary | None = None
        if isinstance(q, dict):
            try:
                summary = QualitySummary.model_validate(q)
            except Exception:
                summary = None
        return cls(
            batch_id=str(batch_row["batch_id"]),
            source_filename=batch_row.get("source_filename"),
            row_count=int(batch_row.get("row_count") or 0),
            sha256=batch_row.get("sha256"),
            ingest_status=batch_row.get("ingest_status"),
            quality_summary=summary,
            created_at=batch_row.get("created_at"),
            columns=columns,
            rows=rows,
        )


class CsvImportResult(BaseModel):
    batch: CsvBatchListItem
    message: str
    quality_summary: QualitySummary | None = None
    duplicate_file: bool = False


class CsvPreviewResult(BaseModel):
    """Vista previa sin escribir en BD (útil para validar antes de importar)."""

    columns: list[str]
    total_rows: int
    sample_rows: list[CsvRowOut]
    sha256_hex: str
    quality_summary: QualitySummary


class DataQualityIssueOut(BaseModel):
    issue_id: str
    dataset: str
    issue_type: str
    severity: str
    row_ref: str | None
    details: dict[str, Any]
    created_at: datetime | None


class PipelineEventOut(BaseModel):
    event_id: str
    stage: str
    status: str
    message: str
    payload_ref: str | None
    created_at: datetime | None


def _row_fingerprint(row: dict[str, str]) -> str:
    normalized = tuple(sorted((k, (v or "").strip()) for k in sorted(row.keys())))
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True)


def analyze_csv_quality(columns: list[str], data_rows: list[dict[str, str]]) -> QualitySummary:
    n = len(data_rows)
    if n == 0:
        return QualitySummary(column_count=len(columns), row_count=0, alerts=["Sin filas de datos"])

    empty_columns: list[str] = []
    for col in columns:
        if all((row.get(col) or "").strip() == "" for row in data_rows):
            empty_columns.append(col)

    rows_with_blank = 0
    for row in data_rows:
        if any((row.get(c) or "").strip() == "" for c in columns):
            rows_with_blank += 1

    completeness = 1.0 - (rows_with_blank / n) if n else 1.0

    fp_map: dict[str, list[int]] = {}
    for i, row in enumerate(data_rows, start=1):
        fp = _row_fingerprint(row)
        fp_map.setdefault(fp, []).append(i)

    dup_groups = [positions for positions in fp_map.values() if len(positions) > 1]
    duplicate_row_groups_count = len(dup_groups)
    dup_sample: list[int] = []
    for grp in dup_groups[:15]:
        dup_sample.extend(sorted(grp)[:5])

    alerts: list[str] = []
    if empty_columns:
        alerts.append(f"Columnas vacías en todas las filas: {', '.join(empty_columns[:12])}")
    if rows_with_blank:
        pct = round(100 * rows_with_blank / n, 2)
        alerts.append(f"{rows_with_blank} filas tienen al menos una celda vacía ({pct}% del total)")
    if duplicate_row_groups_count:
        alerts.append(
            f"{duplicate_row_groups_count} grupo(s) de filas duplicadas (mismo contenido en todas las columnas)"
        )
    if completeness < 0.7:
        alerts.append("Advertencia: muchas filas incompletas; revisad mapeo de columnas o origen.")

    return QualitySummary(
        column_count=len(columns),
        row_count=n,
        empty_columns=sorted(empty_columns),
        rows_with_any_blank_cell=rows_with_blank,
        completeness_ratio=round(completeness, 4),
        duplicate_row_groups=duplicate_row_groups_count,
        duplicate_positions_sample=sorted(set(dup_sample))[:40],
        alerts=alerts,
    )


def _maybe_archive_csv_raw(*, batch_id: str, filename: str, raw_bytes: bytes) -> None:
    """
    Copia opcional del CSV crudo en MinIO (tracabilidad objeto + PostgreSQL).
    Desactivado si MINIO_CSV_INGEST_DISABLED=1 o falta configuración MinIO en env.
    """
    if os.getenv("MINIO_CSV_INGEST_DISABLED", "").strip().lower() in {"1", "true", "yes"}:
        return
    endpoint = os.getenv("MINIO_ENDPOINT")
    ak = os.getenv("MINIO_ACCESS_KEY")
    sk = os.getenv("MINIO_SECRET_KEY")
    if not endpoint or ak is None or sk is None:
        return
    try:
        from minio import Minio
        from minio.error import S3Error
    except ImportError:
        return

    host = endpoint.replace("http://", "").replace("https://", "")
    secure = endpoint.startswith("https://")
    bucket = os.getenv("MINIO_CSV_INGEST_BUCKET", "hospital-csv-ingest")
    client = Minio(host, access_key=ak, secret_key=sk, secure=secure)
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
    except S3Error as e:
        _log.warning("minio bucket csv ingest: %s", e)
        return

    fn = os.path.basename(_SAFE_FILENAME.sub("_", filename) or "import.csv")[:220]
    key = f"ingest/{batch_id}/{fn}"
    bio = io.BytesIO(raw_bytes)
    try:
        client.put_object(
            bucket,
            key,
            bio,
            length=len(raw_bytes),
            content_type="text/csv; charset=utf-8",
            metadata={"sha256": hashlib.sha256(raw_bytes).hexdigest()},
        )
    except S3Error as e:
        _log.warning("minio put csv failed: %s", e)


def _emit_pipeline_event(
    conn,
    *,
    stage: str,
    status: str,
    message: str,
    payload_ref: str | None = None,
) -> None:
    conn.execute(
        text(
            """
            INSERT INTO pipeline_events (event_id, stage, status, message, study_id, payload_ref)
            VALUES (gen_random_uuid(), :stage, :status, :message, NULL, :pref)
            """
        ),
        {"stage": stage, "status": status, "message": message[:2000], "pref": payload_ref},
    )


def emit_csv_ingestion_failure(message: str, exc: BaseException | None = None) -> None:
    """Registra error de ingesta cuando la petición falla fuera del flujo HTTP 4xx habitual."""
    body = message[:1400]
    if exc is not None:
        body = f"{body} | {type(exc).__name__}: {str(exc)[:380]}"
    try:
        with engine().begin() as conn:
            _emit_pipeline_event(
                conn,
                stage="csv_ingestion",
                status="error",
                message=body,
                payload_ref=None,
            )
    except Exception:
        _log.exception("csv_ingestion_failure_event_skipped")


def _emit_data_quality_issues(
    conn,
    *,
    batch_id: str,
    quality: QualitySummary,
    fp_map_duplicate_positions: dict[str, list[int]],
) -> None:
    emitted = 0
    ds = f"csv_import:{batch_id}"

    if quality.empty_columns and emitted < _MAX_DQ_ISSUES_PER_IMPORT:
        conn.execute(
            text(
                """
                INSERT INTO data_quality_issues (issue_id, dataset, issue_type, severity, study_id, row_ref, details)
                VALUES (
                  gen_random_uuid(),
                  CAST(:dataset AS text),
                  'empty_columns',
                  'info',
                  NULL,
                  NULL,
                  CAST(:details AS jsonb)
                )
                """
            ),
            {
                "dataset": ds,
                "details": json.dumps({"columns": quality.empty_columns}, ensure_ascii=False),
            },
        )
        emitted += 1

    for positions in fp_map_duplicate_positions.values():
        if emitted >= _MAX_DQ_ISSUES_PER_IMPORT:
            break
        if len(positions) < 2:
            continue
        conn.execute(
            text(
                """
                INSERT INTO data_quality_issues (issue_id, dataset, issue_type, severity, study_id, row_ref, details)
                VALUES (
                  gen_random_uuid(),
                  CAST(:dataset AS text),
                  'duplicate_rows',
                  'warning',
                  NULL,
                  CAST(:row_ref AS text),
                  CAST(:details AS jsonb)
                )
                """
            ),
            {
                "dataset": ds,
                "row_ref": str(min(positions)),
                "details": json.dumps({"positions": sorted(positions)}, ensure_ascii=False),
            },
        )
        emitted += 1


def _build_duplicate_map(data_rows: list[dict[str, str]]) -> dict[str, list[int]]:
    fp_map: dict[str, list[int]] = {}
    for i, row in enumerate(data_rows, start=1):
        fp = _row_fingerprint(row)
        fp_map.setdefault(fp, []).append(i)
    return fp_map


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


async def preview_csv_upload(file: UploadFile, preview_limit: int = _MAX_PREVIEW_ROWS) -> CsvPreviewResult:
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

    cols, data_rows = _parse_csv_text(textdata)
    quality = analyze_csv_quality(cols, data_rows)
    lim = min(max(1, preview_limit), 100)
    sample = [
        CsvRowOut(position=i, fields=dict(r))
        for i, r in enumerate(data_rows[:lim], start=1)
    ]
    sha = hashlib.sha256(raw_b).hexdigest()
    return CsvPreviewResult(
        columns=cols,
        total_rows=len(data_rows),
        sample_rows=sample,
        sha256_hex=sha,
        quality_summary=quality,
    )


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

    cols, data_rows = _parse_csv_text(textdata)
    fn = (file.filename or "importacion.csv")[:200]
    fn = _SAFE_FILENAME.sub("_", fn) or "importacion.csv"
    sha = hashlib.sha256(raw_b).hexdigest()
    quality = analyze_csv_quality(cols, data_rows)
    fp_dup = _build_duplicate_map(data_rows)

    uid = uuid.UUID(user.user_id)
    with engine().begin() as conn:
        existing = conn.execute(
            text(
                """
                SELECT batch_id, source_filename, row_count, sha256, created_at,
                       ingest_status, quality_summary
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
                quality_summary=item.quality_summary,
                duplicate_file=True,
            )

        ingest_status = "completed_with_warnings" if quality.alerts else "completed"

        owns_new_rows = False
        try:
            b_row = conn.execute(
                text(
                    """
                    INSERT INTO csv_import_batches (user_id, source_filename, row_count, sha256, quality_summary, ingest_status)
                    VALUES (:uid, :fn, :rc, :sha, CAST(:qs AS jsonb), :istatus)
                    RETURNING batch_id, source_filename, row_count, sha256, created_at,
                              ingest_status, quality_summary
                    """
                ),
                {
                    "uid": str(uid),
                    "fn": fn,
                    "rc": len(data_rows),
                    "sha": sha,
                    "qs": quality.model_dump_json(),
                    "istatus": ingest_status,
                },
            ).mappings().fetchone()
            owns_new_rows = True
        except IntegrityError:
            b_row = conn.execute(
                text(
                    """
                    SELECT batch_id, source_filename, row_count, sha256, created_at,
                           ingest_status, quality_summary
                    FROM csv_import_batches
                    WHERE user_id = :uid AND sha256 = :sha
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {"uid": str(uid), "sha": sha},
            ).mappings().fetchone()
            owns_new_rows = False
        assert b_row is not None
        bid = str(b_row["batch_id"])

        if owns_new_rows:
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

            _emit_pipeline_event(
                conn,
                stage="csv_ingestion",
                status="ok" if ingest_status == "completed" else ingest_status,
                message=f"Lote CSV importado: {len(data_rows)} filas, archivo {fn}",
                payload_ref=bid,
            )

            dup_only = {k: v for k, v in fp_dup.items() if len(v) > 1}
            if dup_only or quality.empty_columns:
                _emit_data_quality_issues(conn, batch_id=bid, quality=quality, fp_map_duplicate_positions=dup_only)

    if owns_new_rows:
        try:
            _maybe_archive_csv_raw(batch_id=bid, filename=file.filename or fn, raw_bytes=raw_b)
        except Exception as e:
            _log.warning("csv minio archive non-fatal: %s", e)
        item = CsvBatchListItem.from_row(b_row)
        return CsvImportResult(
            batch=item,
            message=f"Importadas {item.row_count} filas.",
            quality_summary=quality,
            duplicate_file=False,
        )

    item = CsvBatchListItem.from_row(b_row)
    return CsvImportResult(
        batch=item,
        message="Este CSV ya fue importado (condición concurrente detectada); se devuelve el lote existente.",
        quality_summary=item.quality_summary or quality,
        duplicate_file=True,
    )


def count_user_csv_imports(user: UserOut) -> int:
    uid = str(uuid.UUID(user.user_id))
    with engine().connect() as conn:
        n = conn.execute(
            text(
                """
                SELECT COUNT(*)::int AS n
                FROM csv_import_batches
                WHERE user_id = :uid
                """
            ),
            {"uid": uid},
        ).mappings().fetchone()
    return int((n or {}).get("n") or 0)


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
                SELECT batch_id, source_filename, row_count, sha256, created_at,
                       ingest_status, quality_summary
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
                SELECT batch_id, source_filename, row_count, sha256, created_at,
                       ingest_status, quality_summary
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


def list_batch_quality_issues(batch_id: str, user: UserOut, limit: int = 100) -> list[DataQualityIssueOut]:
    """Issues registrados durante la ingesta para un lote (prefijo dataset csv_import:{batch_id})."""
    try:
        bid = str(uuid.UUID(batch_id))
    except ValueError as e:
        raise HTTPException(status_code=400, detail="ID de lote no válido") from e

    uid = str(uuid.UUID(user.user_id))
    ds = f"csv_import:{bid}"
    lim = min(max(1, limit), 500)

    with engine().connect() as conn:
        owner = conn.execute(
            text("SELECT 1 FROM csv_import_batches WHERE batch_id = :bid AND user_id = :uid"),
            {"bid": bid, "uid": uid},
        ).scalar()
        if not owner:
            raise HTTPException(status_code=404, detail="Lote no encontrado")

        rows = conn.execute(
            text(
                """
                SELECT issue_id, dataset, issue_type, severity, row_ref, details, created_at
                FROM data_quality_issues
                WHERE dataset = CAST(:dataset AS text)
                ORDER BY created_at DESC
                LIMIT :lim
                """
            ),
            {"dataset": ds, "lim": lim},
        ).mappings().all()

    out: list[DataQualityIssueOut] = []
    for r in rows:
        d = r.get("details")
        details = dict(d) if isinstance(d, dict) else {}
        out.append(
            DataQualityIssueOut(
                issue_id=str(r["issue_id"]),
                dataset=str(r["dataset"]),
                issue_type=str(r["issue_type"]),
                severity=str(r["severity"]),
                row_ref=r.get("row_ref"),
                details=details,
                created_at=r.get("created_at"),
            )
        )
    return out


def list_csv_pipeline_events(limit: int = 50) -> list[PipelineEventOut]:
    lim = min(max(1, limit), 200)
    with engine().connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT event_id, stage, status, message, payload_ref, created_at
                FROM pipeline_events
                WHERE stage IN ('csv_ingestion')
                ORDER BY created_at DESC
                LIMIT :lim
                """
            ),
            {"lim": lim},
        ).mappings().all()
    return [
        PipelineEventOut(
            event_id=str(r["event_id"]),
            stage=str(r["stage"]),
            status=str(r["status"]),
            message=str(r["message"]),
            payload_ref=r.get("payload_ref"),
            created_at=r.get("created_at"),
        )
        for r in rows
    ]
