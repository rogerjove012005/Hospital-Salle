import os

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from minio import Minio
from sqlalchemy import text

from .auth import (
    CreateUserRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    SelfRegisterRequest,
    TokenResponse,
    UserOut,
    create_user,
    ensure_admin_seed,
    get_current_user,
    register_self,
    list_users,
    login,
    request_password_reset,
    reset_password,
    require_roles,
)
from .csv_aggregates_stats import CsvSparkAggregatesOut, get_csv_spark_aggregates
from .radiology import router as radiology_router
from .dashboard_ops import (
    DashboardSummaryOut,
    OperationalAlertOut,
    get_dashboard_summary,
    hospital_report_response,
    list_operational_alerts,
)
from .dashboard_imports import (
    CsvBatchDetail,
    CsvImportResult,
    CsvPreviewResult,
    DataQualityIssueOut,
    PipelineEventCreate,
    PipelineEventOut,
    count_user_csv_imports,
    emit_csv_ingestion_failure,
    export_user_csv_batch,
    get_csv_batch_detail,
    import_csv_file,
    list_batch_quality_issues,
    list_csv_pipeline_events,
    list_user_csv_imports,
    preview_csv_upload,
    record_pipeline_event,
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

app.include_router(radiology_router)


def _minio_client() -> Minio:
    endpoint = os.environ["MINIO_ENDPOINT"].replace("http://", "").replace("https://", "")
    access_key = os.environ["MINIO_ACCESS_KEY"]
    secret_key = os.environ["MINIO_SECRET_KEY"]
    secure = os.environ["MINIO_ENDPOINT"].startswith("https://")
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/pipeline")
def health_pipeline():
    """
    Estado ligero del último job PySpark de agregados (sin autenticación, para monitorización básica).
    """
    try:
        with engine().connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT computed_at, total_rows::bigint AS total_rows,
                           batches_with_rows::int AS batches_with_rows
                    FROM csv_spark_run_summary
                    WHERE id = 1
                    """
                ),
            ).mappings().fetchone()
        if not row:
            return {"status": "unknown", "spark_aggregates": None}
        r = dict(row)
        ca = r.get("computed_at")
        if ca is not None and hasattr(ca, "isoformat"):
            ca_out = ca.isoformat()
        else:
            ca_out = str(ca) if ca is not None else None
        return {
            "status": "ok",
            "spark_aggregates": {
                "computed_at": ca_out,
                "total_rows": int(r.get("total_rows") or 0),
                "batches_with_rows": int(r.get("batches_with_rows") or 0),
            },
        }
    except Exception as exc:
        return {"status": "degraded", "detail": str(exc)[:400]}


@app.get("/stats/csv-aggregates", response_model=CsvSparkAggregatesOut)
def stats_csv_aggregates(top: int = 15, user: UserOut = Depends(get_current_user)):
    """
    Métricas del último job PySpark sobre datos CSV ingestados (ver tablas csv_spark_*).
    """
    if top < 1 or top > 100:
        raise HTTPException(status_code=400, detail="top debe estar entre 1 y 100")
    return get_csv_spark_aggregates(user, top=top)


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


@app.post("/auth/forgot-password", response_model=ForgotPasswordResponse)
def auth_forgot_password(req: ForgotPasswordRequest):
    return request_password_reset(req)


@app.post("/auth/reset-password", response_model=ResetPasswordResponse)
def auth_reset_password(req: ResetPasswordRequest):
    return reset_password(req)


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


@app.get("/medicos/me")
def get_my_medico(user: UserOut = Depends(require_roles("medico"))):
    if not user.medico_id:
        return None
    with engine().connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT medico_id, full_name, phone, date_of_birth, sex, created_at
                FROM medicos
                WHERE medico_id = :mid
                """
            ),
            {"mid": user.medico_id},
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


def _imports_csv_validate_upload(file: UploadFile) -> None:
    content_type = (file.content_type or "").lower().strip()
    allowed = {
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
        "text/plain",
    }
    if content_type and content_type not in allowed:
        raise HTTPException(status_code=415, detail="Tipo de fichero no soportado. Sube un CSV.")
    if file.filename and not file.filename.lower().endswith(".csv") and content_type not in {"text/plain"}:
        raise HTTPException(status_code=415, detail="Extensión no válida. Sube un fichero .csv.")


@app.post("/imports/csv/preview", response_model=CsvPreviewResult)
async def imports_csv_preview(
    file: UploadFile = File(...),
    preview_limit: int = 25,
    _user: UserOut = Depends(get_current_user),
):
    """
    Parsea CSV y calcula métricas de calidad sin escribir filas ni lotes en BD.
    """
    _imports_csv_validate_upload(file)
    plim = preview_limit if 1 <= preview_limit <= 100 else 25
    return await preview_csv_upload(file, preview_limit=plim)


@app.post("/imports/csv", response_model=CsvImportResult)
async def imports_csv(
    file: UploadFile = File(...),
    user: UserOut = Depends(get_current_user),
):
    _imports_csv_validate_upload(file)
    try:
        return await import_csv_file(file, user)
    except HTTPException:
        raise
    except Exception as e:
        emit_csv_ingestion_failure("Fallo inesperado en importación CSV", e)
        raise HTTPException(
            status_code=500,
            detail="No se pudo completar la ingesta. Inténtalo de nuevo o contacta soporte.",
        ) from e


@app.get("/imports/csv/{batch_id}/quality-issues", response_model=list[DataQualityIssueOut])
def imports_csv_quality_issues(
    batch_id: str,
    limit: int = 100,
    user: UserOut = Depends(get_current_user),
):
    return list_batch_quality_issues(batch_id, user, limit=limit)


@app.get("/dashboard/summary", response_model=DashboardSummaryOut)
def dashboard_summary(user: UserOut = Depends(get_current_user)):
    return get_dashboard_summary(user)


@app.get("/alerts", response_model=list[OperationalAlertOut])
def operational_alerts(
    limit: int = 30,
    _user: UserOut = Depends(require_roles("admin", "medico")),
):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit debe estar entre 1 y 100")
    return list_operational_alerts(limit=limit)


@app.get("/reports/hospital")
def hospital_operational_report(_user: UserOut = Depends(require_roles("admin", "medico"))):
    return hospital_report_response(_user)


@app.get("/admin/imports/pipeline-events", response_model=list[PipelineEventOut])
def admin_csv_pipeline_events(
    limit: int = 50,
    _admin: UserOut = Depends(require_roles("admin")),
):
    return list_csv_pipeline_events(limit=limit)


@app.post("/imports/pipeline-events", response_model=PipelineEventOut)
def imports_record_pipeline_event(
    body: PipelineEventCreate,
    _user: UserOut = Depends(require_roles("admin", "medico")),
):
    return record_pipeline_event(
        stage=body.stage,
        status=body.status,
        message=body.message,
        payload_ref=body.payload_ref,
    )


@app.get("/imports/csv")
def imports_csv_list(
    limit: int = 20,
    offset: int = 0,
    user: UserOut = Depends(get_current_user),
    response: Response = None,
):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit debe estar entre 1 y 100")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset debe ser >= 0")
    total = count_user_csv_imports(user)
    if response is not None:
        response.headers["X-Total-Count"] = str(total)
    return list_user_csv_imports(user, limit=limit, offset=offset)


@app.get("/imports/csv/{batch_id}/export")
def imports_csv_export(batch_id: str, user: UserOut = Depends(get_current_user)):
    """Descarga el lote como CSV regenerado desde las filas persistidas (UTF-8 con BOM)."""
    body, filename = export_user_csv_batch(batch_id, user)
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@app.get("/imports/csv/{batch_id}", response_model=CsvBatchDetail)
def imports_csv_detail(
    batch_id: str,
    rows_limit: int = 200,
    user: UserOut = Depends(get_current_user),
):
    if rows_limit < 1 or rows_limit > 1000:
        raise HTTPException(status_code=400, detail="rows_limit debe estar entre 1 y 1000")
    return get_csv_batch_detail(batch_id, user, rows_limit=rows_limit)

