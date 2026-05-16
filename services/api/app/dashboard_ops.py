"""Resumen operativo, alertas e informes del hospital (visualización + automatización)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from .auth import UserOut
from .csv_aggregates_stats import get_csv_spark_aggregates
from .db import engine
from .dashboard_imports import PipelineEventOut, list_csv_pipeline_events


class OperationalAlertOut(BaseModel):
    event_id: str
    stage: str
    status: str
    message: str
    severity: str
    created_at: datetime | None = None


class DashboardSummaryOut(BaseModel):
    role: str
    patients_count: int | None = None
    studies_count: int | None = None
    csv_import_batches: int | None = None
    pipeline_status: str
    spark_total_rows: int | None = None
    spark_batches: int | None = None
    spark_computed_at: datetime | None = None
    open_alerts: int = 0
    radiology_available: bool = False
    radiology_accuracy: float | None = None


def _severity_for_status(status: str) -> str:
    s = (status or "").lower()
    if s in {"error", "failed", "critical"}:
        return "critical"
    if s in {"warning", "warn", "completed_with_warnings"}:
        return "warning"
    return "info"


def list_operational_alerts(*, limit: int = 30) -> list[OperationalAlertOut]:
    events = list_csv_pipeline_events(limit=limit * 2)
    out: list[OperationalAlertOut] = []
    for e in events:
        sev = _severity_for_status(e.status)
        if sev == "info" and e.status.lower() in {"ok", "completed"}:
            continue
        out.append(
            OperationalAlertOut(
                event_id=e.event_id,
                stage=e.stage,
                status=e.status,
                message=e.message,
                severity=sev,
                created_at=e.created_at,
            )
        )
    with engine().connect() as conn:
        dq = conn.execute(
            text(
                """
                SELECT issue_id::text, dataset, issue_type, severity, details, created_at
                FROM data_quality_issues
                WHERE severity IN ('warning', 'error', 'critical')
                ORDER BY created_at DESC
                LIMIT :lim
                """
            ),
            {"lim": max(5, limit // 2)},
        ).mappings().all()
    for row in dq:
        out.append(
            OperationalAlertOut(
                event_id=str(row["issue_id"]),
                stage="data_quality",
                status=str(row["severity"]),
                message=f"{row['dataset']}: {row['issue_type']}",
                severity=str(row["severity"]) if row["severity"] in {"warning", "error", "critical"} else "warning",
                created_at=row.get("created_at"),
            )
        )
    out.sort(
        key=lambda a: a.created_at or datetime.fromtimestamp(0, tz=timezone.utc),
        reverse=True,
    )
    return out[:limit]


def _count_scalar(conn, sql: str, params: dict | None = None) -> int:
    row = conn.execute(text(sql), params or {}).mappings().fetchone()
    if not row:
        return 0
    val = next(iter(row.values()))
    return int(val or 0)


def get_dashboard_summary(user: UserOut) -> DashboardSummaryOut:
    pipeline_status = "unknown"
    spark_rows: int | None = None
    spark_batches: int | None = None
    spark_at: datetime | None = None
    patients_count: int | None = None
    studies_count: int | None = None
    csv_batches: int | None = None
    rx_available = False
    rx_acc: float | None = None

    with engine().connect() as conn:
        if user.role in {"admin", "medico"}:
            patients_count = _count_scalar(conn, "SELECT COUNT(*) FROM patients")
            studies_count = _count_scalar(conn, "SELECT COUNT(*) FROM studies")
            csv_batches = _count_scalar(conn, "SELECT COUNT(*) FROM csv_import_batches")
        elif user.role == "paciente" and user.patient_id:
            studies_count = _count_scalar(
                conn,
                "SELECT COUNT(*) FROM studies WHERE patient_id = :pid",
                {"pid": user.patient_id},
            )

        row = conn.execute(
            text(
                """
                SELECT computed_at, total_rows::bigint AS total_rows,
                       batches_with_rows::int AS batches_with_rows
                FROM csv_spark_run_summary WHERE id = 1
                """
            )
        ).mappings().fetchone()
        if row:
            pipeline_status = "ok"
            spark_at = row.get("computed_at")
            spark_rows = int(row.get("total_rows") or 0)
            spark_batches = int(row.get("batches_with_rows") or 0)
        else:
            pipeline_status = "degraded"

    if user.role in {"admin", "medico"}:
        try:
            from pathlib import Path
            import json

            rp = Path(__file__).resolve().parent.parent / "models" / "radiology" / "evaluation_report.json"
            if rp.is_file():
                rx_available = True
                with rp.open(encoding="utf-8") as f:
                    data = json.load(f)
                a = data.get("accuracy")
                if a is not None:
                    rx_acc = float(a)
        except Exception:
            pass

    alerts = list_operational_alerts(limit=50)
    open_alerts = len([a for a in alerts if a.severity in {"critical", "warning"}])

    return DashboardSummaryOut(
        role=user.role,
        patients_count=patients_count,
        studies_count=studies_count,
        csv_import_batches=csv_batches,
        pipeline_status=pipeline_status,
        spark_total_rows=spark_rows if user.role in {"admin", "medico"} else None,
        spark_batches=spark_batches if user.role in {"admin", "medico"} else None,
        spark_computed_at=spark_at if user.role in {"admin", "medico"} else None,
        open_alerts=open_alerts if user.role in {"admin", "medico"} else 0,
        radiology_available=rx_available if user.role in {"admin", "medico"} else False,
        radiology_accuracy=rx_acc if user.role in {"admin", "medico"} else None,
    )


def build_hospital_report_html(user: UserOut) -> str:
    summary = get_dashboard_summary(user)
    alerts = list_operational_alerts(limit=20)
    spark_block = ""
    if user.role in {"admin", "medico"}:
        try:
            agg = get_csv_spark_aggregates(user, top=10)
            rows = "".join(
                f"<tr><td>{b.batch_id}</td><td>{b.row_count}</td></tr>" for b in agg.top_batches
            )
            spark_block = f"""
            <h2>Agregados PySpark (CSV)</h2>
            <p>Filas totales: <strong>{agg.summary.total_rows}</strong> ·
            Lotes: <strong>{agg.summary.batches_with_rows}</strong></p>
            <table><thead><tr><th>Lote</th><th>Filas</th></tr></thead><tbody>{rows or '<tr><td colspan="2">Sin datos</td></tr>'}</tbody></table>
            """
        except Exception as exc:
            spark_block = f'<p class="warn">Spark no disponible: {exc}</p>'

    alert_rows = "".join(
        f"<tr><td>{a.severity}</td><td>{a.stage}</td><td>{a.status}</td><td>{a.message[:120]}</td></tr>"
        for a in alerts
    ) or "<tr><td colspan='4'>Sin alertas recientes</td></tr>"

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"/><title>Informe operativo — laSalle</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#1c1917}}
h1{{color:#0f766e}} table{{width:100%;border-collapse:collapse;margin:1rem 0}}
th,td{{border:1px solid #e7e1d8;padding:8px;text-align:left;font-size:0.9rem}}
th{{background:#f5f0e7}} .warn{{color:#b91c1c}} .meta{{color:#78716c;font-size:0.85rem}}
</style></head><body>
<h1>Informe operativo del hospital</h1>
<p class="meta">Generado {now} · Sesión {user.email} · Rol {user.role}</p>
<h2>Resumen</h2>
<ul>
<li>Estado pipeline: <strong>{summary.pipeline_status}</strong></li>
<li>Pacientes: <strong>{summary.patients_count if summary.patients_count is not None else '—'}</strong></li>
<li>Estudios: <strong>{summary.studies_count if summary.studies_count is not None else '—'}</strong></li>
<li>Lotes CSV: <strong>{summary.csv_import_batches if summary.csv_import_batches is not None else '—'}</strong></li>
<li>Alertas abiertas: <strong>{summary.open_alerts}</strong></li>
<li>Radiología IA: <strong>{'disponible' if summary.radiology_available else 'no disponible'}</strong>
{f' (accuracy test {summary.radiology_accuracy:.1%})' if summary.radiology_accuracy is not None else ''}</li>
</ul>
{spark_block}
<h2>Alertas y eventos recientes</h2>
<table><thead><tr><th>Severidad</th><th>Etapa</th><th>Estado</th><th>Mensaje</th></tr></thead>
<tbody>{alert_rows}</tbody></table>
<p class="meta">Informe académico · sin valor clínico · RGPD</p>
</body></html>"""


def hospital_report_response(user: UserOut) -> HTMLResponse:
    html = build_hospital_report_html(user)
    filename = f"informe-hospital-{datetime.now(timezone.utc).strftime('%Y%m%d')}.html"
    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
