# Diario de desarrollo con IA — laSalle Health Center

**Herramienta principal:** [Cursor](https://cursor.com) (agente Auto, edición inline, búsqueda semántica en repo)  
**Metodología:** Spec-Driven Development — specs en `docs/specs/` antes de implementar módulos críticos  
**Periodo:** Abril–Mayo 2026

---

## 1. Herramientas utilizadas y justificación

| Herramienta | Uso | Por qué |
|-------------|-----|---------|
| **Cursor** | Generación de API, workers, Docker, docs, tests | Contexto de todo el repo, iteración rápida, terminal integrado |
| **Git** | Versionado y ramas (`feature/finalize`) | Trazabilidad de lo generado vs. corregido |
| **Docker Compose** | Validación local del stack | La IA propone servicios; el humano verifica `up --build` |

No se usó Copilot de forma exclusiva; Cursor cubre el rol de «IA obligatoria» del enunciado.

---

## 2. Ejemplos representativos de prompts

### 2.1 Ingesta CSV (SDD → código)

**Prompt (resumido):**

> Escribe un worker Python que cada N segundos descargue CSV desde URLs en `CSV_PULL_URLS`, vigile una carpeta inbox, haga login JWT contra FastAPI y llame a `POST /imports/csv`. Debe ser idempotente con estado JSON, mover ficheros a processed/failed y loguear JSON por línea.

**Resultado:** `pipelines/ingestion/automated_csv_ingest.py` (~300 líneas) funcional en primera iteración.

**Corrección humana:** Ajustar timeouts para CSV grandes; enlazar `post_pipeline_event` en errores.

### 2.2 PySpark agregaciones

**Prompt:**

> Crea `spark_aggregate.py` que lea `csv_import_rows` por JDBC desde Postgres, agrupe por batch_id, escriba en `csv_aggregates` y guarde Parquet en volumen. Master local[*], sin UI Spark.

**Resultado:** Script alineado con el enunciado Big Data.

**Corrección:** Escapar columna `position` (palabra reservada SQL) en subconsulta JDBC.

### 2.3 Centro de control

**Prompt:**

> Añade endpoints `/dashboard/summary`, `/alerts` y `/reports/hospital` en FastAPI, y página analytics.html con Chart.js que consuma JWT del portal.

**Resultado:** `dashboard_ops.py` + frontend. Ver [`2026-05-operaciones-dashboard.md`](2026-05-operaciones-dashboard.md).

### 2.4 Radiología — matriz de confusión

**Prompt:**

> Documenta en SPECIFICATIONS.md el reto de clasificación triple, EfficientNetB4, criterios de aceptación y sección ética. Genera `clinical_analysis.py` que interprete falsos negativos COVID.

**Resultado:** Spec completa + análisis clínico exportado a JSON.

---

## 3. Casos donde la IA acertó

- Estructura **docker-compose** multi-servicio con healthchecks y redes.
- Esquema SQL inicial (`01-init.sql`) con tablas de pipeline y calidad.
- Tests de humo API (`tests/test_api_smoke.py`) y huella de fila CSV.
- Documentación ADR y diagramas Mermaid coherentes con el código existente.
- Refactor de `dashboard_imports.py` para emitir `data_quality_issues`.

---

## 4. Casos donde hubo que corregir o iterar

| Problema | Causa | Solución |
|----------|-------|----------|
| `POST /imports/csv` → 500 | Bug en construcción de huella (`row[k]` vs variable incorrecta) | Fix manual + test `test_row_fingerprint.py` |
| Build API falla en otro PC | Faltaban scripts ML en Git | Commitear `bootstrap_model.py` y Dockerfiles pipeline |
| Emails `.local` rechazados | Validación Pydantic estricta | `validate_academic_email` para dominios docentes |
| Gráficos analytics vacíos | Spark aún no había corrido | Documentar esperar 1 ciclo o importar CSV antes de demo |
| Enlace roto en diario | `pipeline-dataflow.md` no existía | Crear `docs/architecture/pipeline-dataflow.md` |

---

## 5. Reflexión crítica

### Qué aportó la IA

- **Velocidad:** componentes repetitivos (boilerplate FastAPI, Docker, README) en horas en lugar de días.
- **Consistencia:** nombres y patrones alineados entre API, workers y docs.
- **Exploración:** alternativas (Dask vs Spark) documentadas en ADRs tras preguntas dirigidas.

### Limitaciones encontradas

- No sustituye criterio clínico ni validación estadística rigurosa.
- A veces asume rutas o ficheros que aún no están commiteados.
- Modelos DL pesados: la IA propone arquitecturas; el entrenamiento real sigue dependiendo de GPU/tiempo local.

### Cómo se superaron

- Specs SDD explícitas antes de pedir código grande.
- Tests automáticos y `docker compose up` como «fuente de verdad».
- Revisión humana de seguridad (JWT, roles, no commitear `.env`).

---

## 6. Impacto en productividad (estimación)

| Tarea | Sin IA (est.) | Con Cursor (est.) | Ahorro |
|-------|---------------|-------------------|--------|
| Worker ingesta + compose | 2 días | 4–6 h | ~60 % |
| Módulo dashboard + UI | 1,5 días | 5 h | ~55 % |
| Documentación ADR/SDD/diario | 1 día | 2 h | ~75 % |
| Pipeline ML (esqueleto) | 3 días | 1,5 días | ~50 % |

**Calidad del código:** adecuada para proyecto académico; requiere revisión en producción (tipos, seguridad, hardening).

---

## 7. Relación con SDD

Cada módulo mayor tiene spec en `docs/specs/` con inputs, outputs, restricciones y criterios de aceptación. El flujo fue:

1. Redactar spec (humano + IA).
2. Prompt de implementación referenciando la spec.
3. Verificar criterios de aceptación con demo o test.

---

## 8. Referencias

- [`docs/specs/`](../specs/)
- [`ml/radiology-classifier/SPECIFICATIONS.md`](../../ml/radiology-classifier/SPECIFICATIONS.md)
- [`docs/MEMORIA_TECNICA.md`](../MEMORIA_TECNICA.md)
