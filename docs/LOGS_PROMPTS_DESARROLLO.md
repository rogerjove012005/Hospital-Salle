# Registro de prompts y logs — Proyecto Hospital laSalle

> Diario reconstruido del desarrollo asistido por IA (Cursor Agent).  
> Proyecto: **Proyecto_Hospital** · Stack: FastAPI, PostgreSQL, Docker, vanilla JS, scikit-learn.

---

## Índice

1. [Sesión 01 — Arranque del monorepo](#sesión-01--arranque-del-monorepo)
2. [Sesión 02 — Portal y autenticación](#sesión-02--portal-y-autenticación)
3. [Sesión 03 — Ingesta CSV y PostgreSQL](#sesión-03--ingesta-csv-y-postgresql)
4. [Sesión 04 — Pipeline Spark y calidad](#sesión-04--pipeline-spark-y-calidad)
5. [Sesión 05 — Radiología asistida](#sesión-05--radiología-asistida)
6. [Sesión 06 — Modelo de enfermedad (árbol + CV)](#sesión-06--modelo-de-enfermedad-árbol--cv)
7. [Sesión 07 — UI, altas clínicas y ML Studio](#sesión-07--ui-altas-clínicas-y-ml-studio)

---

## Sesión 01 — Arranque del monorepo

**Fecha simulada:** 2026-05-10 · **Duración:** ~2 h

### Prompt usuario

```text
Necesito un proyecto hospitalario con API FastAPI, PostgreSQL y frontend.
Que corra con Docker Compose y tenga datos de prueba.
```

### Log agente

```log
[10:12:01] INFO  Explorando workspace vacío
[10:12:15] OK    Creado infra/docker/docker-compose.yml (postgres, api, frontend, minio)
[10:14:33] OK    infra/db/01-init.sql — tablas patients, medicos, app_users, studies
[10:18:02] WARN  MinIO bucket no existía → script init en entrypoint
[10:22:41] OK    services/api/app/main.py — health + CORS
[10:25:09] OK    docker compose up → postgres healthy, api :8000
```

### Prompt usuario

```text
Añade README con cómo levantar el entorno en local.
```

### Respuesta resumida

Documentado `docker compose up` desde `infra/docker`, puertos 3000/8000/5432, usuario seed admin.

---

## Sesión 02 — Portal y autenticación

**Fecha simulada:** 2026-05-12

### Prompt usuario

```text
Haz login con JWT, roles paciente/medico/admin y sidebar en el frontend.
```

### Log agente

```log
[14:02:11] INFO  auth.py — hash bcrypt, login, register_self
[14:08:44] OK    portal.js — PORTAL_PAGES, buildNavSections(), initPortalApp()
[14:11:20] OK    landing.html + index.html redirección
[14:15:03] ERROR Test login 401 — email no normalizado
[14:15:18] FIX   _normalize_email() aplicado en login y register
[14:16:01] OK    Token Bearer en localStorage, fetch /auth/me
```

### Prompt usuario

```text
Los médicos deben ver pacientes asignados y el admin todos.
```

```log
[15:40:22] OK    GET /patients con require_roles("admin","medico")
[15:42:10] OK    patients.html tabla data-table
```

---

## Sesión 03 — Ingesta CSV y PostgreSQL

**Fecha simulada:** 2026-05-14

### Prompt usuario

```text
Quiero ingesta CSV: preview sin guardar, importar lote, listar lotes.
Que guarde en tablas csv_import_* y sincronice pacientes.
```

### Log agente

```log
[09:01:00] INFO  dashboard_imports.py — CsvPreviewResult, CsvImportResult
[09:12:33] OK    POST /imports/csv/preview?preview_limit=15
[09:18:55] OK    POST /imports/csv — deduplicación SHA-256
[09:25:10] OK    csv_patient_sync.py — upsert patients por patient_reference
[09:31:44] OK    imports.html + imports.js — vista previa JSON (temporal)
```

### Prompt usuario

```text
Al importar debe actualizar medicos y usuarios también, no solo patients.
```

```log
[11:05:12] OK    csv_domain_sync.py — DomainSyncStats
[11:06:01] OK    Columnas: enfermedad, medico_id, email, role
[11:08:19] OK    domain_sync en respuesta CsvImportResult
```

---

## Sesión 04 — Pipeline Spark y calidad

**Fecha simulada:** 2026-05-16

### Prompt usuario

```text
Pipeline completo: limpieza, ingesta, transformación tipo Spark y análisis.
Guíame paso a paso en la UI.
```

### Log agente

```log
[16:20:00] OK    csv_pipeline.py — run_full_csv_pipeline()
[16:28:11] OK    POST /imports/csv/pipeline/transform — csv_spark_batch_row_counts
[16:35:40] OK    imports.js — PIPELINE_ORDER 5 pasos, pipeline-rail, pipeline-steps
[16:42:03] OK    GET /stats/csv-aggregates — gráficos barras por lote
[16:48:22] WARN  Usuario repite mismo CSV → mensaje duplicate_file + resync domain
```

### Prompt usuario

```text
Ficheros CSV de referencia para probar sin inventar datos.
```

```log
[17:10:05] OK    public/samples/referencia_enfermedades.csv (20 filas, columna enfermedad)
[17:10:06] OK    referencia_pacientes, urgencias, calidad, citas, ingesta_demo_1
```

---

## Sesión 05 — Radiología asistida

**Fecha simulada:** 2026-05-17

### Prompt usuario

```text
Clasificador RX: Sana, Neumonía, COVID-19. Subir imagen y ver probabilidades.
```

### Log agente

```log
[10:00:00] INFO  ml/radiology-classifier — sklearn Pipeline PCA+MLP
[10:15:22] OK    radiology.py — POST /radiology/predict
[10:22:18] OK    Dockerfile stage radiology-build — bootstrap_model.py
[10:30:44] OK    radiology.html — Chart.js barras probabilidades
[10:38:01] OK    Matriz confusión PNG en /radiology/charts/confusion-matrix
```

### Prompt usuario

```text
Mejora el modelo, acepta PNG y dame imágenes de prueba.
```

```log
[14:12:00] OK    generate_synthetic_radiology.py — patrones más contrastados
[14:18:33] OK    samples/rx/rx_demo_sana.png, rx_demo_neumonia.png, rx_demo_covid.png
[14:25:11] FIX   Safari no asignaba File al input → rxSelectedFile + auto-analyze
[14:28:40] OK    Validación PNG por magic bytes \x89PNG
```

---

## Sesión 06 — Modelo de enfermedad (árbol + CV)

**Fecha simulada:** 2026-05-18 (mañana)

### Prompt usuario

```text
Modelo que prediga enfermedad del paciente con árbol de decisiones y cross validation.
```

### Log agente

```log
[08:30:00] OK    patient_disease_ml.py — DecisionTreeClassifier
[08:32:15] OK    StratifiedKFold + cross_val_score(accuracy)
[08:35:40] OK    Features: age, sex, department → primary_diagnosis
[08:40:02] OK    POST /ml/patient-disease/train
[08:41:10] OK    GET /metrics, /predictions, /predict/{patient_id}
[08:45:22] WARN  Solo 20 muestras / 14 clases → CV 2 folds, accuracy baja (esperado)
```

### Prompt usuario (pipeline)

```text
Que el pipeline guarde en user, medico y que el paso final entrene el ML.
```

```log
[09:10:00] OK    Paso 5 pipeline → POST /ml/patient-disease/train
[09:12:33] OK    renderSyncKpis + renderMlKpis en imports.js
```

---

## Sesión 07 — UI, altas clínicas y ML Studio

**Fecha simulada:** 2026-05-18 (tarde)

### Prompt usuario

```text
La UI de ingesta se ve mal, detalle de lote más completo, sección para altas
de pacientes y médicos, y documento MD con logs del desarrollo con prompts.
```

### Log agente

```log
[15:00:00] OK    directory.html — pestañas paciente/médico, fieldsets
[15:08:12] OK    POST /clinic/patients, POST /clinic/medicos
[15:15:44] FIX   overflow:hidden en cards → tablas cortadas
[15:22:01] OK    loadDetail ampliado — KPIs, column_fill, quality issues
[15:30:00] OK    docs/LOGS_PROMPTS_DESARROLLO.md (este archivo)
```

### Prompt usuario

```text
Mejora el modelo visualmente: botón reentrenar, porcentajes y gráficos.
```

```log
[15:35:10] OK    patient_disease_ml — confusion_matrix, per_class_metrics, feature_importance
[15:38:22] OK    imports.html — bloque #mlStudio (Chart.js)
[15:40:55] OK    imports.js — retrainMlModel(), 4 gráficos + matriz HTML
[15:42:18] OK    Gráficos: CV folds, distribución clases, F1, importancia variables
[15:43:01] OK    Tabla predicciones recientes con confianza %
```

---

## Comandos útiles (extraídos de logs)

```bash
# Entorno
cd infra/docker && docker compose up -d

# Entrenar modelo enfermedad (API)
curl -X POST http://localhost:8000/ml/patient-disease/train \
  -H "Authorization: Bearer $TOKEN"

# Importar CSV enfermedades
curl -X POST http://localhost:8000/imports/csv \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@services/frontend/public/samples/referencia_enfermedades.csv"

# Radiología predict
curl -X POST http://localhost:8000/radiology/predict \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@services/frontend/public/samples/rx/rx_demo_sana.png"
```

---

## Métricas finales (entorno demo)

| Componente | Estado |
|------------|--------|
| API `/health` | OK |
| Pacientes en BD | ~20+ tras referencia_enfermedades |
| ML enfermedad CV accuracy | Variable (pocas muestras/clase) |
| RX sklearn | OK en Docker build |
| Frontend | localhost:3000 |

---

## Notas éticas (registro obligatorio)

- Modelo RX y ML enfermedad: **uso académico**, no diagnóstico clínico.
- Datos sintéticos / CSV demo; no sustituyen historiales reales.
- Disclaimer visible en radiología y en informes del portal.

---

*Documento generado para memoria del proyecto · laSalle Health Center · 2026.*
