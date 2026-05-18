# Guía de demostración — laSalle Health Center

Documento para defender el proyecto ante profesores: qué enseñar, en qué orden, comandos de terminal y **por qué** está hecho así.

---

## 0. Estado de Git (antes de la demo)

### ¿Está todo commiteado?

| Situación | Detalle |
|-----------|---------|
| **`main` vs `origin/main`** | Sincronizado en el último push (`a141e33`) |
| **Cambios pendientes** | **Sí** — hay ficheros **en staging** (listos para commit) que **no están en GitHub** |
| **Sin seguimiento** | Datos locales (`sample_*.png`, `spark-processed-output/`, `models/`) — **no conviene commitearlos** |

### Ficheros en staging (recomendado commitear antes de la defensa)

- `pipelines/ingestion/Dockerfile`, `requirements.txt`, `samples/export.csv`
- `pipelines/processing/Dockerfile`, `run_loop.sh`, `spark_aggregate.py`
- Scripts y entrenamiento de `ml/radiology-classifier/` (necesarios para `docker compose build api`)

Sin este commit, en otro ordenador **`docker compose up --build` puede fallar** (faltan Dockerfiles del pipeline).

### Comandos para commitear (opcional, tú decides)

```bash
cd /Users/rogerjove/Desktop/Proyecto_Hospital

# Ver qué se subiría
git status

# Commit solo lo ya preparado (staging)
git commit -m "$(cat <<'EOF'
fix(infra): restaura pipelines Docker y scripts ML para build reproducible

Incluye worker CSV, job PySpark y bootstrap del modelo de radiología en la imagen API.
EOF
)"

git push origin main
```

**No hagas** `git add` de `ml/radiology-classifier/data/` ni de `infra/docker/spark-processed-output/` (pesados o generados).

---

## 1. Mensaje de elevator (30 segundos)

> «**laSalle Health Center** es un portal hospitalario con roles (paciente, médico, admin), ingesta **automatizada** de CSV desde un sistema legacy simulado, agregación **PySpark**, **centro de control** con alertas e informes, y un módulo de **IA** para clasificar radiografías de tórax en tres clases. Todo corre en **Docker Compose**: Postgres, MinIO, API FastAPI y frontend nginx. Es un proyecto académico: datos sintéticos, sin valor clínico real.»

---

## 2. Mapa de features ↔ enunciado

| Feature del encargo | Dónde se demuestra | Tecnología elegida | Por qué |
|---------------------|-------------------|--------------------|---------|
| Portal / acceso | `http://localhost:3000` | HTML + JS + nginx | Simple, desplegable, sin framework pesado |
| Roles y seguridad | Login + menú distinto por rol | JWT + FastAPI | Estándar REST, stateless, fácil de probar con `curl` |
| Ingesta CSV | Worker + página Imports | Python worker + `POST /imports/csv` | Simula hospital externo vía HTTP y carpeta inbox |
| Big Data / Spark | Logs + `/health/pipeline` | PySpark `local[*]` | Cumple requisito de procesamiento distribuido en modo docente sin cluster |
| Calidad de datos | Alertas + quality-summary | Postgres `data_quality_issues` | Trazabilidad auditable, enlazada al lote CSV |
| Automatización | Informe HTML + worker | Cron en contenedor + API | Informe bajo demanda; ingesta periódica |
| Visualización | Centro de control | Chart.js + KPIs API | Gráficos sin stack BI pesado |
| IA radiología | `/radiology.html` | sklearn en API (CNN documentado aparte) | Inferencia rápida en Docker; CNN como prototipo investigación |
| Observabilidad | `/health/observability` | Logs Docker + endpoints health | Monitorización ligera exigida en práctica |
| Ética / RGPD | Docs + disclaimers en UI | Markdown | Transparencia y límites del modelo |
| Documentación | `docs/`, ADR, SDD | Markdown en repo | Trazabilidad de decisiones (SDD) |

---

## 3. Preparación (terminal) — 5 minutos antes

### 3.1 Arrancar el stack

```bash
cd /Users/rogerjove/Desktop/Proyecto_Hospital/infra/docker

# Primera vez o tras cambios
docker compose --env-file .env.example up -d --build

# Solo reinicio
docker compose --env-file .env.example up -d
```

**Qué debe salir:** contenedores `api`, `frontend`, `postgres`, `minio`, `mailpit`, `mock-hospital-feed`, `csv-ingest-worker`, `spark-csv-aggregate`, `pgadmin` en estado `Up` (API `healthy`).

```bash
docker compose ps
```

### 3.2 Comprobar salud (para ti, no hace falta enseñar todo)

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
curl -s http://localhost:8000/health/pipeline | python3 -m json.tool
curl -s http://localhost:8000/health/observability | python3 -m json.tool
```

**Qué significa:**

- `/health` → API viva.
- `/health/pipeline` → último job Spark escribió agregados (`total_rows`, `batches_with_rows`).
- `/health/observability` → Postgres + MinIO + contadores operativos (lotes CSV, errores 7 días, incidencias calidad).

### 3.3 Credenciales de demo

| Rol | Email | Contraseña | Uso en demo |
|-----|-------|------------|-------------|
| **Admin** | `rogerjove012005@gmail.com` | `hospital` | Todo el portal + imports + informes |
| **Médico** | `medico500@example.com` | `hospital` | RX, pacientes, alertas (si falla, usar admin) |
| **Paciente** | `fronttest@hospital.local` | `hospital` | Vista reducida, expediente propio |

*(Otras cuentas existen en BD; estas son las más fiables para la demo.)*

### 3.4 URLs que debes tener abiertas en pestañas

| Pestaña | URL |
|---------|-----|
| Portal login | http://localhost:3000 |
| API Swagger | http://localhost:8000/docs |
| Centro de control | http://localhost:3000/analytics.html |
| Radiología | http://localhost:3000/radiology.html |
| Presentación HTML | Abrir archivo `docs/slides/presentacion-hospital.html` en el navegador |
| Mailpit (opcional) | http://localhost:8025 |
| MinIO consola (opcional) | http://localhost:9001 |

---

## 4. Guión de demostración (≈ 12–15 min)

### Bloque A — Arquitectura con terminal (2 min)

**Qué hacer:**

```bash
cd /Users/rogerjove/Desktop/Proyecto_Hospital
tree -L 2 -d infra services pipelines ml automation docs 2>/dev/null || ls infra services pipelines ml docs
```

**Qué decir:**

- `infra/docker` → orquestación.
- `services/api` + `services/frontend` → capa de aplicación.
- `pipelines/` → ingesta y Spark (Big Data).
- `ml/radiology-classifier` → modelo IA.
- `automation/` → informes, alertas, file-mover.
- `docs/` → SDD, ADR, ética, diario IA.

**Razonamiento:** estructura alineada con el PDF del encargo para que el corrector encuentre cada entregable.

---

### Bloque B — Pipeline de datos sin UI (3 min)

#### B.1 Feed hospitalario simulado

```bash
curl -s http://localhost:8099/export.csv | head -5
```

**Qué sale:** CSV con cabecera `patient_reference,department,...` y 2 filas de ejemplo.

**Por qué:** el enunciado pide simular un sistema hospitalario externo; nginx sirve un CSV fijo como si fuera una API legacy.

#### B.2 Ingesta manual vía API (demuestra el endpoint)

```bash
export API=http://localhost:8000
export TOKEN=$(curl -s -X POST "$API/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"rogerjove012005@gmail.com","password":"hospital"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST "$API/imports/csv" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/Users/rogerjove/Desktop/Proyecto_Hospital/pipelines/ingestion/samples/export.csv;type=text/csv" \
  | python3 -m json.tool
```

**Qué sale:** JSON con `batch_id`, `row_count`, `quality_summary`, mensaje de éxito o lote duplicado (SHA256).

**Por qué:** demuestra API REST, autenticación, persistencia en Postgres y reglas de calidad en la misma transacción.

#### B.3 Worker automatizado (opcional, logs)

```bash
cd /Users/rogerjove/Desktop/Proyecto_Hospital/infra/docker
docker compose logs csv-ingest-worker --tail=15
```

**Qué sale:** JSON de eventos (`startup`, `skipped_unchanged_url` o ingesta OK).

**Por qué:** cumple **automatización**: el contenedor descarga la URL del feed cada ~90 s y llama al mismo endpoint.

#### B.4 PySpark

```bash
curl -s http://localhost:8000/health/pipeline | python3 -m json.tool
docker compose logs spark-csv-aggregate --tail=10
```

**Qué sale:** `status: ok`, miles de filas agregadas en `csv_spark_run_summary`.

**Por qué:** separar **ingesta** (filas crudas) de **agregación** (Spark lee Postgres, escribe resúmenes + Parquet) es el patrón lakehouse docente.

#### B.5 Eventos y calidad (admin)

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "$API/admin/imports/pipeline-events?limit=5" | python3 -m json.tool

curl -s -H "Authorization: Bearer $TOKEN" \
  "$API/admin/imports/quality-summary" | python3 -m json.tool
```

**Qué sale:** lista de etapas (`csv_ingestion`, `spark_csv_aggregate`) y resumen de incidencias.

---

### Bloque C — Portal web (5 min)

Abre **http://localhost:3000**

#### C.1 Login admin

1. Email: `rogerjove012005@gmail.com` / contraseña: `hospital`
2. Entrar al portal.

**Qué sale:** `landing.html` — panel con accesos rápidos, estadísticas demo, spotlight de radiología.

**Por qué:** un solo front con **shell** común (`portal.js`): sidebar, cabecera, cierre de sesión.

#### C.2 Recorrido por rol (admin)

| Orden | Página | Qué enseñar | Mensaje clave |
|-------|--------|-------------|---------------|
| 1 | **Mi panel** | Accesos rápidos | UX hospitalaria unificada |
| 2 | **Centro de control** | KPIs, gráficos Spark/RX, alertas, botón informe | Visualización + operaciones |
| 3 | **Ingesta CSV** | Subir CSV o ver lotes | Puente negocio ↔ datos |
| 4 | **Radiología** | Métricas JSON, gráfico F1, matriz, subir imagen | IA asistida, no diagnóstico |
| 5 | **Directorio pacientes** | Listado (admin/médico) | RBAC clínico |
| 6 | **Mi perfil / Agenda / Contacto** | Datos de sesión y formulario | Completitud del portal |
| 7 | **Generar informe HTML** (en Centro de control) | Se abre informe en nueva pestaña | Automatización de informes |

#### C.3 Login paciente (1 min)

Cerrar sesión → login `fronttest@hospital.local` / `hospital`.

**Qué sale:** menú sin «Directorio pacientes» ni «Ingesta CSV»; centro de control resumido.

**Por qué:** **minimización RGPD** — el paciente no ve operaciones ni datos de otros.

Demostración rápida en terminal (opcional):

```bash
PAT=$(curl -s -X POST "$API/auth/login" -H 'Content-Type: application/json' \
  -d '{"email":"fronttest@hospital.local","password":"hospital"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -o /dev/null -w "alerts: %{http_code}\n" -H "Authorization: Bearer $PAT" "$API/alerts"
# Debe ser 403
```

---

### Bloque D — Inteligencia artificial (3 min)

#### D.1 En el navegador — `radiology.html`

1. Métricas del modelo (JSON): accuracy, F1 por clase.
2. Gráfico de barras F1.
3. Imagen matriz de confusión.
4. Subir PNG/JPEG → **Analizar radiografía**.

**Qué sale:** `predicted_class`, probabilidades, disclaimer legal.

**Por qué cada pieza:**

| Elemento | Razonamiento |
|----------|--------------|
| Tres clases Sana / Neumonía / COVID-19 | Literal del encargo |
| Matriz de confusión | Evaluación exigible; muestra errores por clase |
| Disclaimer | Ética: probabilidad ≠ diagnóstico |
| sklearn en producción | Arranque rápido en Docker; baseline interpretable |
| CNN en `CNN_QUICKSTART.md` | Segunda vía DL para nota de investigación |

#### D.2 En terminal — predict

```bash
# Copiar una imagen de prueba desde el contenedor API (matriz generada en build)
docker cp docker-api-1:/app/models/radiology/confusion_matrix.png /tmp/rx-demo.png

curl -s -X POST "$API/radiology/metrics" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

curl -s -X POST "$API/radiology/predict" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/rx-demo.png;type=image/png" | python3 -m json.tool
```

---

### Bloque E — Documentación y cierre (2 min)

**En el repo (VS Code o GitHub):**

| Ruta | Para qué |
|------|----------|
| `docs/specs/` | SDD por módulo |
| `docs/adr/` | Decisiones (Spark local, sklearn, CNN) |
| `docs/ethics/` | Ética RX + sistema global |
| `docs/ai-dev-diary/` | Uso de IA en el desarrollo |
| `docs/slides/presentacion-hospital.html` | Diapositivas de defensa |
| `docs/architecture/pipeline-dataflow.md` | Flujo end-to-end |
| `Informe_Hospital_Salle.pdf` / `Presentacion_Hospital_Salle.pptx` | Entregables en raíz (si aplican) |
| `Practica_IA_BigData_Hospital_v3.docx` | Memoria (no versionada en Git si está en `.gitignore`) |

**Frase de cierre:**

> «El sistema es reproducible con un solo `docker compose up`, trazable por eventos en base de datos, y separa claramente datos, procesamiento, visualización e IA con documentación y límites éticos explícitos.»

---

## 5. Lista completa de features demostrables

### 5.1 Infraestructura

- [ ] Docker Compose multi-servicio
- [ ] Postgres persistente
- [ ] MinIO (archivo CSV opcional)
- [ ] Mailpit (correo dev)
- [ ] pgAdmin `:5050` (opcional)

### 5.2 API REST (Swagger: `/docs`)

- [ ] Auth: login, registro, forgot/reset password
- [ ] Pacientes y estudios por rol
- [ ] CSV: preview, import, listado, detalle, export, quality-issues
- [ ] Dashboard: summary, alerts, informe hospital
- [ ] Admin: users, pipeline-events, quality-summary
- [ ] Health: `/health`, `/health/deps`, `/health/pipeline`, `/health/observability`
- [ ] Stats: `/stats/csv-aggregates`
- [ ] Radiología: `/radiology/metrics`, `/predict`, `/charts/confusion-matrix`

### 5.3 Frontend (portal)

- [ ] `index.html` — login / registro
- [ ] `landing.html` — panel por rol
- [ ] `analytics.html` — centro de control
- [ ] `imports.html` — ingesta CSV
- [ ] `radiology.html` — IA RX
- [ ] `patients.html`, `profile.html`, `agenda.html`, `records.html`, `contact.html`

### 5.4 Pipelines y automatización

- [ ] mock-hospital-feed
- [ ] csv-ingest-worker
- [ ] spark-csv-aggregate
- [ ] `automation/reports/generate_hospital_report.py`
- [ ] `automation/file-mover/move_ingest_files.py`

### 5.5 ML / investigación

- [ ] Modelo empaquetado en imagen API
- [ ] Scripts en `ml/radiology-classifier/`
- [ ] Prototipo CNN documentado

### 5.6 Tests

```bash
cd /Users/rogerjove/Desktop/Proyecto_Hospital
PYTHONPATH=services/api python3 -m pytest tests/test_row_fingerprint.py -q

# Con API levantada (requiere pytest instalado)
pip3 install -r tests/requirements-test.txt --break-system-packages  # o en venv
pytest tests/ -m integration -v
```

---

## 6. Cheat sheet — comandos únicos

```bash
# Ir al compose
cd /Users/rogerjove/Desktop/Proyecto_Hospital/infra/docker

# Estado
docker compose ps

# Logs en vivo
docker compose logs -f api
docker compose logs -f csv-ingest-worker
docker compose logs -f spark-csv-aggregate

# Parar todo
docker compose down

# Token admin rápido
export API=http://localhost:8000
export TOKEN=$(curl -s -X POST "$API/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"rogerjove012005@gmail.com","password":"hospital"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Informe HTML a fichero
curl -s -H "Authorization: Bearer $TOKEN" "$API/reports/hospital" -o /tmp/informe-hospital.html
open /tmp/informe-hospital.html   # macOS
```

---

## 7. Problemas frecuentes en la demo

| Síntoma | Causa probable | Solución rápida |
|---------|----------------|-----------------|
| `docker compose build` falla en API | Faltan scripts ML en el repo | Commitear staging o `git checkout feature/radiografia-rx -- ml/radiology-classifier/scripts` |
| `POST /imports/csv` → 500 | Bug antiguo en huella de fila | Asegurar código actual en `dashboard_imports.py` (`row[k]` no `v`) |
| Login `.local` → 422 | EmailStr estricto | Versión con `validate_academic_email` |
| Gráficos vacíos en analytics | Sin datos Spark | Esperar 1 ciclo del contenedor spark o importar CSV antes |
| RX predict falla | Imagen no PNG/JPEG | Usar imagen 224×224 aprox. |
| Puerto ocupado | Otro compose | `docker compose down` o cambiar puertos en `.env.example` |

---

## 8. Checklist rápido pre-entrega (nota orientativa)

| Área | Estado tras finalize |
|------|----------------------|
| Infra Docker | Hecho |
| Ingesta + API CSV | Hecho |
| PySpark | Hecho |
| Portal + RBAC | Hecho |
| Centro de control | Hecho |
| IA RX | Hecho |
| Automatización | Hecho |
| Docs / ética / diario | Hecho |
| Presentación HTML | Hecho |
| Tests | Hecho |
| Notebooks | No (omitido) |
| **Nota orientativa** | **~8,7 / 10** |

---

## 9. Orden sugerido si solo tienes 5 minutos

1. `docker compose ps` + `/health/observability`
2. Login admin → Centro de control → Informe
3. Radiología → predict
4. `curl` import CSV o mostrar Imports en UI
5. Abrir `docs/slides/presentacion-hospital.html` o PDF de memoria

---

*Proyecto académico — laSalle Health Center · sin valor clínico real · datos de demostración.*
