"""Orquestación del pipeline CSV: ingesta → limpieza → transformación → análisis."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any

from fastapi import HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .auth import UserOut
from .csv_aggregates_stats import CsvSparkAggregatesOut, get_csv_spark_aggregates
from .csv_domain_sync import DomainSyncStats, sync_domain_from_csv_rows
from .dashboard_imports import DomainSyncOut
from .dashboard_imports import (
    CsvBatchListItem,
    CsvImportResult,
    CsvPreviewResult,
    CsvRowOut,
    QualitySummary,
    _MAX_CSV_BYTES,
    _MAX_PREVIEW_ROWS,
    _SAFE_FILENAME,
    _build_duplicate_map,
    _emit_data_quality_issues,
    _emit_pipeline_event,
    _maybe_archive_csv_raw,
    _parse_csv_text,
    analyze_csv_quality,
)
from .db import engine


class PipelineStepOut(BaseModel):
    stage: str
    label: str
    status: str
    message: str
    duration_ms: int | None = None


class FullCsvPipelineResult(BaseModel):
    steps: list[PipelineStepOut] = Field(default_factory=list)
    preview: CsvPreviewResult | None = None
    import_result: CsvImportResult | None = None
    aggregates: CsvSparkAggregatesOut | None = None
    batch_id: str | None = None
    domain_sync: DomainSyncOut | None = None
    ml_metrics: dict | None = None
    total_duration_ms: int = 0


def _step(
    steps: list[PipelineStepOut],
    *,
    stage: str,
    label: str,
    status: str,
    message: str,
    t0: float,
) -> None:
    steps.append(
        PipelineStepOut(
            stage=stage,
            label=label,
            status=status,
            message=message,
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
    )


def preview_csv_bytes(raw_b: bytes, preview_limit: int = _MAX_PREVIEW_ROWS) -> CsvPreviewResult:
    if not raw_b:
        raise HTTPException(status_code=400, detail="El fichero está vacío")
    if len(raw_b) > _MAX_CSV_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"El fichero supera {_MAX_CSV_BYTES // (1024 * 1024)} MB.",
        )
    try:
        textdata = raw_b.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=400, detail="El CSV debe estar en UTF-8") from e

    cols, data_rows = _parse_csv_text(textdata)
    quality = analyze_csv_quality(cols, data_rows)
    lim = min(max(1, preview_limit), 100)
    sample = [CsvRowOut(position=i, fields=dict(r)) for i, r in enumerate(data_rows[:lim], start=1)]
    sha = hashlib.sha256(raw_b).hexdigest()
    return CsvPreviewResult(
        columns=cols,
        total_rows=len(data_rows),
        sample_rows=sample,
        sha256_hex=sha,
        quality_summary=quality,
    )


def import_csv_bytes(raw_b: bytes, filename: str, user: UserOut) -> CsvImportResult:
    if not raw_b:
        raise HTTPException(status_code=400, detail="El fichero está vacío")
    if len(raw_b) > _MAX_CSV_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"El fichero supera {_MAX_CSV_BYTES // (1024 * 1024)} MB.",
        )
    try:
        textdata = raw_b.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=400, detail="El CSV debe estar en UTF-8") from e

    cols, data_rows = _parse_csv_text(textdata)
    fn = _SAFE_FILENAME.sub("_", (filename or "importacion.csv")[:200]) or "importacion.csv"
    sha = hashlib.sha256(raw_b).hexdigest()
    quality = analyze_csv_quality(cols, data_rows)
    fp_dup = _build_duplicate_map(data_rows)

    uid = uuid.UUID(user.user_id)
    owns_new_rows = False
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
            bid = str(existing["batch_id"])
            domain_stats = sync_domain_from_csv_rows(conn, cols, data_rows)
            _emit_pipeline_event(
                conn,
                stage="csv_ingestion",
                status="ok",
                message=f"Lote conocido reutilizado ({item.row_count} filas)",
                payload_ref=bid,
            )
            _emit_pipeline_event(
                conn,
                stage="csv_cleaning",
                status="ok",
                message="Calidad ya validada; sincronización clínica ejecutada",
                payload_ref=bid,
            )
            return CsvImportResult(
                batch=item,
                message=(
                    f"Lote ya en base de datos ({item.row_count} filas). "
                    "Tablas patients/medicos/users actualizadas."
                ),
                quality_summary=item.quality_summary,
                duplicate_file=True,
                domain_sync=DomainSyncOut(**domain_stats.__dict__),
            )

        ingest_status = "completed_with_warnings" if quality.alerts else "completed"
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

        if not owns_new_rows:
            domain_stats = sync_domain_from_csv_rows(conn, cols, data_rows)
            item = CsvBatchListItem.from_row(b_row)
            return CsvImportResult(
                batch=item,
                message="Lote existente; tablas clínicas actualizadas.",
                quality_summary=item.quality_summary or quality,
                duplicate_file=True,
                domain_sync=DomainSyncOut(**domain_stats.__dict__),
            )

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
            message=f"Ingesta: {len(data_rows)} filas, archivo {fn}",
            payload_ref=bid,
        )

        dup_only = {k: v for k, v in fp_dup.items() if len(v) > 1}
        dq_count = 0
        if dup_only or quality.empty_columns:
            _emit_data_quality_issues(
                conn, batch_id=bid, quality=quality, fp_map_duplicate_positions=dup_only
            )
            dq_count = len(dup_only) + len(quality.empty_columns)

        domain_stats = sync_domain_from_csv_rows(conn, cols, data_rows)
        clean_status = "warning" if quality.alerts or dq_count else "ok"
        clean_msg = (
            f"Limpieza: completitud {round(quality.completeness_ratio * 100, 1)}%, "
            f"{dq_count} incidencia(s) · BD: +{domain_stats.patients_created} pacientes, "
            f"+{domain_stats.users_created} usuarios"
        )
        _emit_pipeline_event(
            conn,
            stage="csv_cleaning",
            status=clean_status,
            message=clean_msg,
            payload_ref=bid,
        )
        sync_out = DomainSyncOut(**domain_stats.__dict__)

    if owns_new_rows:
        try:
            _maybe_archive_csv_raw(batch_id=bid, filename=filename or fn, raw_bytes=raw_b)
        except Exception:
            pass
        item = CsvBatchListItem.from_row(b_row)
        return CsvImportResult(
            batch=item,
            message=f"Importadas {item.row_count} filas y sincronizadas tablas clínicas.",
            quality_summary=quality,
            duplicate_file=False,
            domain_sync=sync_out,
        )

    item = CsvBatchListItem.from_row(b_row)
    return CsvImportResult(
        batch=item,
        message="Importación completada.",
        quality_summary=quality,
        duplicate_file=False,
        domain_sync=sync_out,
    )


def run_sql_csv_aggregates() -> dict[str, Any]:
    """Transformación analítica (equivalente funcional al job PySpark sobre csv_import_rows)."""
    with engine().begin() as conn:
        conn.execute(text("DELETE FROM csv_spark_batch_row_counts"))
        conn.execute(
            text(
                """
                INSERT INTO csv_spark_batch_row_counts (batch_id, row_count, computed_at)
                SELECT batch_id::text, COUNT(*)::bigint, NOW()
                FROM csv_import_rows
                GROUP BY batch_id
                """
            )
        )
        batches_aggregated = conn.execute(
            text("SELECT COUNT(*)::int FROM csv_spark_batch_row_counts")
        ).scalar_one()
        totals = conn.execute(
            text(
                """
                SELECT COUNT(*)::bigint AS total_rows,
                       COUNT(DISTINCT batch_id)::int AS batches_with_rows
                FROM csv_import_rows
                """
            )
        ).mappings().one()
        conn.execute(text("DELETE FROM csv_spark_run_summary WHERE id = 1"))
        conn.execute(
            text(
                """
                INSERT INTO csv_spark_run_summary (id, computed_at, total_rows, batches_with_rows)
                VALUES (1, NOW(), :total_rows, :batches_with_rows)
                """
            ),
            {
                "total_rows": int(totals["total_rows"] or 0),
                "batches_with_rows": int(totals["batches_with_rows"] or 0),
            },
        )
        _emit_pipeline_event(
            conn,
            stage="csv_transform",
            status="ok",
            message=(
                f"Transformación: agregados por lote ({int(batches_aggregated or 0)} lotes), "
                f"{int(totals['total_rows'] or 0)} filas totales"
            ),
            payload_ref=None,
        )
    return {
        "batches_aggregated": int(batches_aggregated or 0),
        "total_rows": int(totals["total_rows"] or 0),
        "batches_with_rows": int(totals["batches_with_rows"] or 0),
    }


async def run_full_csv_pipeline(file: UploadFile, user: UserOut) -> FullCsvPipelineResult:
    pipeline_t0 = time.perf_counter()
    steps: list[PipelineStepOut] = []
    raw_b = await file.read()
    filename = file.filename or "importacion.csv"

    # 1. Limpieza (análisis de calidad previo)
    t0 = time.perf_counter()
    try:
        preview = preview_csv_bytes(raw_b, preview_limit=12)
        q = preview.quality_summary
        st = "warning" if q and q.alerts else "ok"
        msg = f"{preview.total_rows} filas, {preview.columns and len(preview.columns)} columnas"
        if q:
            msg += f" · completitud {round(q.completeness_ratio * 100, 1)}%"
            if q.alerts:
                msg += f" · {len(q.alerts)} alerta(s)"
        _step(steps, stage="clean", label="Limpieza y calidad", status=st, message=msg, t0=t0)
    except HTTPException:
        raise
    except Exception as e:
        _step(steps, stage="clean", label="Limpieza y calidad", status="error", message=str(e)[:400], t0=t0)
        raise HTTPException(status_code=400, detail=f"Limpieza fallida: {e}") from e

    # 2. Ingesta
    t0 = time.perf_counter()
    try:
        import_result = import_csv_bytes(raw_b, filename, user)
        batch_id = str(import_result.batch.batch_id)
        _step(
            steps,
            stage="ingest",
            label="Ingesta",
            status="ok",
            message=import_result.message,
            t0=t0,
        )
    except HTTPException:
        raise
    except Exception as e:
        _step(steps, stage="ingest", label="Ingesta", status="error", message=str(e)[:400], t0=t0)
        raise HTTPException(status_code=500, detail=f"Ingesta fallida: {e}") from e

    # 3. Transformación
    t0 = time.perf_counter()
    try:
        tx = run_sql_csv_aggregates()
        _emit_pipeline_event_standalone(
            stage="spark_csv_aggregate",
            status="ok",
            message=(
                "Análisis agregado (SQL on-demand; el worker PySpark también recalcula en segundo plano)"
            ),
        )
        _step(
            steps,
            stage="transform",
            label="Transformación",
            status="ok",
            message=(
                f"Agregados: {tx['total_rows']} filas en {tx['batches_with_rows']} lote(s)"
            ),
            t0=t0,
        )
    except Exception as e:
        _step(steps, stage="transform", label="Transformación", status="error", message=str(e)[:400], t0=t0)
        raise HTTPException(status_code=500, detail=f"Transformación fallida: {e}") from e

    # 4. Análisis
    t0 = time.perf_counter()
    try:
        aggregates = get_csv_spark_aggregates(user, top=12)
        s = aggregates.summary
        _step(
            steps,
            stage="analyze",
            label="Análisis",
            status="ok",
            message=(
                f"Métricas listas: {s.total_rows} filas agregadas, "
                f"{s.batches_with_rows} lotes con datos"
            ),
            t0=t0,
        )
        _emit_pipeline_event_standalone(
            stage="csv_analysis",
            status="ok",
            message="Pipeline completo finalizado: ingesta, limpieza, transformación y análisis",
            payload_ref=batch_id,
        )
    except Exception as e:
        _step(steps, stage="analyze", label="Análisis", status="error", message=str(e)[:400], t0=t0)
        raise HTTPException(status_code=500, detail=f"Análisis fallido: {e}") from e

    ml_metrics = None
    try:
        from .patient_disease_ml import train_patient_disease_model

        metrics = train_patient_disease_model(cv_folds=5)
        ml_metrics = metrics.model_dump()
        _step(
            steps,
            stage="ml",
            label="Modelo ML (árbol de decisiones)",
            status="ok",
            message=(
                f"CV accuracy {metrics.cv_accuracy_mean:.1%} "
                f"(±{metrics.cv_accuracy_std:.1%}) · {metrics.n_samples} pacientes"
            ),
            t0=time.perf_counter(),
        )
    except Exception as ml_exc:
        _step(
            steps,
            stage="ml",
            label="Modelo ML",
            status="warning",
            message=str(ml_exc)[:200],
            t0=time.perf_counter(),
        )

    return FullCsvPipelineResult(
        steps=steps,
        preview=preview,
        import_result=import_result,
        aggregates=aggregates,
        batch_id=batch_id,
        domain_sync=import_result.domain_sync if import_result else None,
        ml_metrics=ml_metrics,
        total_duration_ms=int((time.perf_counter() - pipeline_t0) * 1000),
    )


def _emit_pipeline_event_standalone(
    *,
    stage: str,
    status: str,
    message: str,
    payload_ref: str | None = None,
) -> None:
    with engine().begin() as conn:
        _emit_pipeline_event(
            conn,
            stage=stage,
            status=status,
            message=message,
            payload_ref=payload_ref,
        )
