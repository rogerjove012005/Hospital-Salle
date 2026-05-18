# Guía de aprendizaje — laSalle Health Center

Documento para **dominar todo el proyecto**: funcionalidades, radiografías, arquitectura, IA, Big Data, ética y defensa oral.  
Complementa el informe formal (`Informe_Hospital_Salle.pdf`) y la memoria técnica (`MEMORIA_TECNICA.md`).

---

## 1. Resumen en una frase

**laSalle Health Center** es un hospital simulado con portal web por roles, API REST, ingesta automatizada de CSV, agregación PySpark, almacenamiento de imágenes en MinIO, y un **clasificador de radiografías de tórax** (Normal / Neumonía / COVID-19) integrado en Docker. Es un **prototipo académico**, no un producto sanitario certificado.

---

## 2. Qué debes aprender (mapa mental)

```
┌─────────────────────────────────────────────────────────────────┐
│                    laSalle Health Center                          │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│   Portal     │   API REST   │  Big Data    │   IA Radiología    │
│  (nginx)     │  (FastAPI)   │ CSV+Spark    │  sklearn / CNN     │
├──────────────┼──────────────┼──────────────┼────────────────────┤
│ Login/roles  │ JWT + auth   │ Ingesta      │ 3 clases RX        │
│ Pacientes    │ Pacientes    │ Calidad      │ Preprocesado       │
│ Estudios     │ Estudios     │ Agregados    │ Inferencia API     │
│ Centro ctrl  │ Dashboard    │ Alertas      │ Métricas + ética   │
│ Radiología   │ Informes     │ Eventos      │                    │
└──────────────┴──────────────┴──────────────┴────────────────────┘
         │              │              │              │
         └──────────────┴──────────────┴──────────────┘
                              │
                    PostgreSQL + MinIO
                    (Docker Compose)
```

---

## 3. Ruta de aprendizaje recomendada (orden)

| Orden | Tema | Tiempo orientativo | Dónde practicar |
|-------|------|-------------------|-----------------|
| 1 | Levantar el stack Docker | 1 h | `infra/docker/` → `docker compose up` |
| 2 | Portal y roles | 2 h | http://localhost:3000 |
| 3 | API y Swagger | 2 h | http://localhost:8000/docs |
| 4 | Base de datos (tablas y relaciones) | 2 h | pgAdmin :5050 |
| 5 | Ingesta CSV y calidad | 3 h | Imports + worker |
| 6 | PySpark y agregados | 3 h | logs `spark-csv-aggregate` |
| 7 | Radiografías + ML | 4 h | `ml/radiology-classifier/` + `/radiology.html` |
| 8 | Ética, limitaciones, defensa | 2 h | `docs/ethics/`, informe PDF |
| 9 | Documentación ADR/SDD | 1 h | `docs/adr/`, `docs/specs/` |

---

## 4. Tecnologías que debes dominar

### 4.1 Infraestructura y despliegue

| Tecnología | Para qué sirve en el proyecto | Conceptos clave |
|------------|------------------------------|-----------------|
| **Docker** | Empaquetar cada servicio | Imagen, contenedor, volumen, red |
| **Docker Compose** | Orquestar todo con un comando | `depends_on`, healthchecks, `.env` |
| **nginx** | Servir el frontend estático | Puerto 3000, sin backend propio |
| **PostgreSQL 16** | Datos relacionales (pacientes, CSV, eventos) | SQL, FK, JSONB, transacciones ACID |
| **MinIO** | Almacén S3 de radiografías | bucket, key, SDK minio-py |
| **Mailpit** | SMTP de desarrollo (reset password) | Puerto 8025 UI, 1025 SMTP |

### 4.2 Backend

| Tecnología | Uso |
|------------|-----|
| **Python 3.10+** | API, workers, ML |
| **FastAPI** | API REST, validación Pydantic, OpenAPI |
| **SQLAlchemy** | Conexión a PostgreSQL |
| **JWT** | Autenticación stateless (`Authorization: Bearer`) |
| **bcrypt/argon** | Hash de contraseñas (módulo `security.py`) |

### 4.3 Big Data

| Tecnología | Uso |
|------------|-----|
| **PySpark** (`local[*]`) | Agregar filas CSV por `batch_id` |
| **Parquet** | Salida intermedia en `spark-processed-output/` |
| **Worker Python** | Ingesta periódica cada ~90 s desde feed HTTP o carpeta inbox |

### 4.4 Inteligencia artificial

| Tecnología | Uso |
|------------|-----|
| **PIL / NumPy** | Carga y preprocesado de imágenes |
| **scikit-learn** | Pipeline en producción API: `StandardScaler` → `PCA(100)` → `MLPClassifier` |
| **TensorFlow / EfficientNetB4** | CNN documentada como objetivo de producción (`SPECIFICATIONS.md`, `cnn_baseline_torch.py`) |
| **joblib** | Serializar `model_final.pkl` |
| **métricas sklearn** | Accuracy, F1, matriz de confusión, ROC/AUC |

### 4.5 Frontend

| Tecnología | Uso |
|------------|-----|
| **HTML + CSS + JavaScript vanilla** | Portal sin React/Vue |
| **Chart.js** | Gráficos en centro de control y radiología |
| **fetch API** | Llamadas a la API con JWT en cabecera |

---

## 5. Funcionalidades completas del sistema

### 5.1 Portal web (`services/frontend/public/`)

| Página | Archivo | Quién la usa | Qué hace |
|--------|---------|--------------|----------|
| Login / registro | `index.html`, `app.js` | Todos | Login, auto-registro paciente/médico |
| Dashboard | `landing.html`, `landing.js` | Autenticados | Menú según rol |
| Pacientes | `patients.html` | admin, médico | Lista de pacientes |
| Expediente propio | vía API `/patients/me` | paciente | Solo sus datos |
| Estudios / registros | `records.html` | Según rol | Estudios radiológicos |
| Perfil | `profile.html` | Todos | Datos del usuario |
| Agenda | `agenda.html` | UI de citas (académico) |
| Contacto | `contact.html` | Público/informativo |
| **Radiología IA** | `radiology.html`, `radiology.js` | admin, médico | Subir RX, ver predicción y métricas |
| **Imports CSV** | `imports.html` | admin, médico | Subir CSV, preview, ver lotes |
| **Centro de control** | `analytics.html` | admin, médico | KPIs, alertas, gráficos Spark |
| Reset contraseña | `reset-password.html` | Público (con token) | Flujo email |

**Roles y permisos:**

| Rol | Permisos principales |
|-----|----------------------|
| `admin` | Usuarios, todos los pacientes/estudios, imports, dashboard, radiología |
| `medico` | Todos los pacientes/estudios, imports, dashboard, radiología |
| `paciente` | Solo su expediente (`/patients/me`, `/studies/me`) |

### 5.2 API REST (`services/api/app/`)

#### Autenticación (`auth.py`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/auth/login` | Devuelve JWT |
| POST | `/auth/register` | Auto-registro paciente/médico |
| GET | `/auth/me` | Perfil actual |
| POST | `/auth/forgot-password` | Envía email con token (TTL ~30 min) |
| POST | `/auth/reset-password` | Cambia contraseña con token |
| POST | `/admin/users` | Crear usuario (solo admin) |
| GET | `/admin/users` | Listar usuarios (admin) |

#### Dominio clínico

| Método | Ruta | Roles | Descripción |
|--------|------|-------|-------------|
| GET | `/patients` | admin, médico | Lista pacientes |
| GET | `/patients/me` | paciente | Mi expediente |
| GET | `/medicos/me` | médico | Perfil médico |
| GET | `/studies` | admin, médico | Todos los estudios |
| GET | `/studies/me` | paciente | Mis estudios |

#### Big Data / operaciones

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/imports/csv/preview` | Vista previa sin guardar |
| POST | `/imports/csv` | Importar lote CSV |
| GET | `/imports/csv` | Historial de lotes del usuario |
| GET | `/imports/csv/{batch_id}` | Detalle de un lote |
| GET | `/imports/csv/{batch_id}/export` | Exportar lote |
| GET | `/imports/csv/{batch_id}/quality-issues` | Incidencias de calidad |
| POST | `/imports/pipeline-events` | Registrar evento de pipeline |
| GET | `/admin/imports/pipeline-events` | Auditoría (admin) |
| GET | `/admin/imports/quality-summary` | Resumen calidad (admin) |
| GET | `/dashboard/summary` | KPIs centro de control |
| GET | `/alerts` | Alertas operativas |
| GET | `/reports/hospital` | Informe hospital HTML/JSON |
| GET | `/stats/csv-aggregates` | Top agregados PySpark |

#### Salud y monitorización

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | API viva |
| GET | `/health/deps` | Postgres + MinIO |
| GET | `/health/pipeline` | Último job Spark |
| GET | `/health/observability` | Panel ligero (deps + alertas + lotes) |

#### Radiología (`radiology.py`, prefijo `/radiology`)

| Método | Ruta | Roles | Descripción |
|--------|------|-------|-------------|
| GET | `/radiology/metrics` | admin, médico | Accuracy, matriz, highlights clínicos |
| GET | `/radiology/charts/confusion-matrix` | admin, médico | Imagen PNG de confusión |
| POST | `/radiology/predict` | admin, médico | **Inferencia**: sube imagen → clase + probabilidades |

### 5.3 Pipeline de datos (`pipelines/`)

| Etapa | Carpeta / servicio | Qué hace |
|-------|-------------------|----------|
| **Ingesta** | `pipelines/ingestion/`, `csv-ingest-worker` | Descarga CSV del mock hospital o lee carpeta `inbox/` |
| **Almacenamiento** | PostgreSQL | `csv_import_batches`, `csv_import_rows` |
| **Calidad** | Reglas en `dashboard_imports.py` | Duplicados, campos vacíos → `data_quality_issues` |
| **Procesamiento** | `spark-csv-aggregate`, `spark_aggregate.py` | Agrega por `batch_id` → `csv_aggregates` + Parquet |
| **Orquestación** | `pipelines/orchestration/` | Diseño documentado (Airflow futuro) |
| **Trazabilidad** | `pipeline_events` | Cada etapa registra ok/error/warning |

**Flujo CSV end-to-end:**

1. `mock-hospital-feed` (:8099) expone `export.csv`.
2. Worker cada ~90 s hace GET o lee `csv-ingest-mounts/inbox/`.
3. Worker llama `POST /imports/csv` con JWT.
4. API valida filas, calcula huella (`row_fingerprint`), guarda en Postgres.
5. Spark cada ~300 s lee `csv_import_rows`, escribe agregados y evento.
6. Portal muestra KPIs en Centro de control.

### 5.4 Automatizaciones (`automation/`)

| Módulo | Estado | Función |
|--------|--------|---------|
| `file-mover/` | Implementado | Mover ficheros entre carpetas de ingesta |
| `alerts/` | Parcial | Alertas vía logs + endpoint `/alerts` |
| `reports/` | Parcial | `GET /reports/hospital` |
| Email reset password | **Completo** | Mailpit (dev) o SMTP real (Gmail) |

### 5.5 Servicios Docker (memorizar)

| Servicio | Puerto | Función |
|----------|--------|---------|
| frontend | 3000 | Portal nginx |
| api | 8000 | FastAPI |
| postgres | 5432 | Base de datos |
| minio | 9000 / 9001 | Objetos / consola |
| mailpit | 8025 / 1025 | Correo dev |
| pgadmin | 5050 | Admin BBDD |
| mock-hospital-feed | 8099 | CSV simulado |
| csv-ingest-worker | — | Ingesta automática |
| spark-csv-aggregate | — | Job PySpark en bucle |

---

## 6. Radiografías — todo lo que debes saber

### 6.1 Problema clínico (contexto)

Los radiólogos revisan **cientos de radiografías de tórax al día**. La fatiga aumenta errores y retrasa diagnósticos urgentes (neumonía, COVID-19). El sistema propone **triaje asistido por IA**, siempre con supervisión humana.

### 6.2 Las tres clases

| Clase | Carpeta dataset | Significado radiológico (simplificado) |
|-------|-----------------|----------------------------------------|
| **NORMAL** | `data/synthetic/NORMAL/` | Sin hallazgos patológicos evidentes |
| **NEUMONÍA** | `data/synthetic/NEUMONIA/` | Opacidades compatibles con infección |
| **COVID-19** | `data/synthetic/COVID-19/` | Patrones típicos COVID (vidrio esmerilado, etc.) |

### 6.3 Datos

| Fuente | Ubicación | Notas |
|--------|-----------|-------|
| Sintéticas (demo) | `ml/radiology-classifier/data/synthetic/` | 300 imágenes (100/clase), generadas con script |
| Público real | Kaggle *Chest X-Ray COVID-19 & Pneumonia* | Para entrenamiento serio; script `sync_chest_xray_from_downloads.py` |
| En producción futura | PACS hospitalario | Formato DICOM, integración HL7 |

### 6.4 Preprocesado (`training/preprocess.py`)

Debes poder explicar cada paso:

1. **Escala de grises** (`convert("L")`) — las RX son monocromáticas.
2. **Resize 224×224** — estándar para CNN/EfficientNet.
3. **Normalización 0–1** — dividir píxeles entre 255.
4. **Stack a 3 canales RGB** — compatibilidad con modelos ImageNet.
5. **Data augmentation** (solo train): rotación ±20°, desplazamiento ±20%, flip horizontal, brillo ±20%.
6. **Split estratificado**: 70 % train, 10 % val, 20 % test.

### 6.5 Dos modelos (importante para la defensa)

| | **Implementado en API** | **Documentado como producción** |
|---|-------------------------|--------------------------------|
| Arquitectura | sklearn: Scaler → PCA(100) → MLP 256-128-64 | EfficientNetB4 + transfer learning |
| Entrada | Vector aplanado 224×224×3 = 150.528 features | Tensor 4D |
| Ventajas | Rápido, sin GPU, fácil en Docker | Mejor precisión con datos reales |
| Archivos | `training/model.py`, `model_final.pkl` | `SPECIFICATIONS.md`, `cnn_baseline_torch.py` |
| Peso COVID | `class_weight` / sample_weight ~1.5 | Mismo criterio ético |

**Frase para profesores:** *«El flujo completo está en sklearn para la demo reproducible; la CNN EfficientNetB4 es el diseño objetivo con datos reales.»*

### 6.6 Entrenamiento (`training/train.py`)

Pasos que debes dominar:

1. `DataPreprocessor` carga imágenes.
2. `reshape(N, -1)` — **crítico**: sklearn no acepta tensores 4D.
3. `compute_sample_weight` por desbalance de clases.
4. `pipeline.fit()` — encadena Scaler → PCA → MLP.
5. Early stopping (paciencia 15) contra overfitting.
6. `joblib.dump` → `models/model_final.pkl` + JSON metadatos.

Comando:

```bash
cd ml/radiology-classifier
pip install -r requirements.txt
python run_pipeline.py
```

### 6.7 Evaluación (`training/evaluate.py`)

Métricas que debes definir con tus palabras:

| Métrica | Fórmula / idea | Por qué importa |
|---------|----------------|-----------------|
| **Accuracy** | Aciertos / total | Visión global (engañosa si hay desbalance) |
| **Precisión** | TP / (TP+FP) | Cuántos positivos predichos son reales |
| **Recall (sensibilidad)** | TP / (TP+FN) | Cuántos enfermos reales detectamos |
| **F1** | Media armónica P y R | Balance por clase |
| **Especificidad** | TN / (TN+FP) | Cuántos sanos identificamos bien |
| **Matriz de confusión** | Tabla de errores | Ver confusiones NEUMONÍA ↔ COVID |
| **ROC / AUC** | Curva one-vs-rest | Capacidad de discriminación |

**Error más grave:** falso negativo COVID (paciente COVID clasificado como Normal) → priorizar recall en COVID.

Artefactos generados:

- `models/model_final.pkl`
- `training_history.png`, `confusion_matrix.png`, `roc_curves.png`
- `evaluation_report.json`, `clinical_analysis.json`

### 6.8 Inferencia en la API (`radiology.py`)

1. Usuario sube imagen (multipart) en `POST /radiology/predict`.
2. API: PIL → gris → 224×224 → normalizar → stack 3 canales → aplanar.
3. `joblib.load(model_final.pkl)` → probabilidades por clase.
4. Respuesta JSON + **disclaimer ético** en UI.

No sustituye al radiólogo: es **orientativo**.

### 6.9 Almacenamiento de estudios (modelo de datos)

```
patients (patient_id, datos personales)
    └── studies (study_id, image_s3_bucket, image_s3_key, timestamp)
            └── predictions (pred_label, prob_sana, prob_neumonia, prob_covid)
```

MinIO guarda el binario; PostgreSQL guarda la **referencia** (bucket + key), no la imagen embebida.

### 6.10 Limitaciones de las radiografías en este proyecto

- Datos **sintéticos** → métricas no extrapolables a clínica real.
- Modelo **caja negra** (sin Grad-CAM implementado).
- Sin validación por radiólogos.
- Sin integración DICOM/PACS.
- **No usar para decisiones clínicas reales.**

---

## 7. Base de datos — tablas esenciales

| Tabla | Contenido |
|-------|-----------|
| `users` | Login, rol, hash contraseña |
| `patients` | Pacientes del hospital |
| `medicos` | Personal médico |
| `studies` | Estudios RX (referencia MinIO) |
| `predictions` | Salida del modelo por estudio |
| `csv_import_batches` | Metadatos de cada importación CSV |
| `csv_import_rows` | Filas del CSV normalizadas |
| `csv_aggregates` | Resultado PySpark |
| `csv_spark_run_summary` | Última ejecución Spark |
| `data_quality_issues` | Duplicados, campos vacíos, etc. |
| `pipeline_events` | Auditoría de etapas |

Esquema inicial: `infra/db/01-init.sql`.

---

## 8. Seguridad — qué debes saber explicar

1. **JWT** en cabecera `Authorization: Bearer <token>`.
2. **Roles** en cada endpoint (`require_roles`).
3. **Contraseñas**: hash fuerte, política de complejidad en registro.
4. **Reset password**: token de un solo uso, expira en minutos.
5. **CORS** configurable para el frontend.
6. **Separación** datos personales (`patients`) vs imágenes (`studies` + MinIO) — paso hacia seudonimización RGPD.
7. En producción: HTTPS, `JWT_SECRET` fuerte, no commitear `.env`.

---

## 9. Ética y legal (imprescindible en el examen)

### 9.1 Principios

- Prototipo académico, **no diagnóstico automático**.
- Supervisión humana obligatoria.
- Datos sintéticos o públicos en demo; **no subir RX reales de pacientes**.

### 9.2 Sesgos posibles

- Género, edad, marca de equipo RX, geografía, prevalencia de enfermedades.

### 9.3 RGPD (radiografías = datos de salud, art. 9)

- Consentimiento, minimización, DPIA, derecho de supresión, seudonimización.

### 9.4 Riesgos

| Riesgo | Mitigación en diseño |
|--------|---------------------|
| Falso negativo COVID | Peso mayor clase COVID, revisión médica |
| Sobredependencia IA | Disclaimers en UI, formación |
| Fuga de datos | Roles, TLS en producción |
| Model drift | Monitorización (futuro) |

Documentos: `docs/ethics/radiology-ia-etica.md`, `docs/ethics/sistema-hospital-ethica.md`.

---

## 10. Decisiones técnicas (ADR) — memorizar el “por qué”

| Decisión | Por qué | Alternativa descartada |
|----------|---------|------------------------|
| PostgreSQL + MinIO | Relacional + objetos para imágenes | MongoDB (menos ACID) |
| PySpark local | Cumple Big Data sin cluster | Solo pandas (menos “big”) |
| ML en imagen API | Inferencia con `docker compose up` | Microservicio aparte (más complejo) |
| JWT | Stateless, escalable | Redis sesiones |
| HTML estático | Despliegue simple | Streamlit (otro proceso Python) |
| EfficientNet vs ResNet | Mejor ratio precisión/params | ResNet50 más pesado |

ADRs en `docs/adr/001-*.md`, `002-*.md`, `003-*.md`.

---

## 11. Archivos clave del repositorio

| Ruta | Qué aprender ahí |
|------|------------------|
| `README.md` | Inicio rápido y URLs |
| `Informe_Hospital_Salle.pdf` | Informe formal 18 páginas |
| `docs/MEMORIA_TECNICA.md` | Resumen por apartados del enunciado |
| `docs/GUIA_DEMOSTRACION_PROFESORES.md` | Guión de defensa oral |
| `docs/architecture/pipeline-dataflow.md` | Diagrama Mermaid del flujo |
| `infra/docker/docker-compose.yml` | Todos los servicios |
| `services/api/app/main.py` | Rutas principales |
| `services/api/app/auth.py` | JWT, roles, email |
| `services/api/app/radiology.py` | Inferencia RX |
| `services/api/app/dashboard_imports.py` | CSV y calidad |
| `ml/radiology-classifier/run_pipeline.py` | Pipeline ML completo |
| `ml/radiology-classifier/training/*.py` | Preprocess, train, evaluate, model |
| `pipelines/processing/spark_aggregate.py` | Job Spark |
| `tests/test_api_smoke.py` | Tests básicos API |

---

## 12. Comandos prácticos para estudiar

```bash
# Levantar todo
cd infra/docker && cp .env.example .env && docker compose --env-file .env up --build

# Salud
curl -s http://localhost:8000/health | python3 -m json.tool
curl -s http://localhost:8000/health/observability | python3 -m json.tool

# Login (obtener token)
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"rogerjove012005@gmail.com","password":"hospital"}'

# Pipeline ML local
cd ml/radiology-classifier && python run_pipeline.py

# Tests
pip install -r tests/requirements-test.txt
pytest tests/ -q
```

**Credenciales demo:** admin `rogerjove012005@gmail.com` / `hospital`.

---

## 13. Preguntas típicas de defensa (prepara respuesta)

1. **¿Qué problema resuelve el proyecto?**  
   Modernizar gestión hospitalaria con Big Data + IA para triaje de radiografías y análisis de datos operativos CSV.

2. **¿Por qué tres clases en RX?**  
   Normal, Neumonía y COVID-19 — patologías con presentación radiológica relevante y dataset público disponible.

3. **¿Por qué sklearn y no solo CNN?**  
   Demo reproducible sin GPU; CNN documentada para producción con datos reales.

4. **¿Cómo fluye una radiografía desde subida hasta predicción?**  
   Frontend → `POST /radiology/predict` → preprocesado → modelo pkl → JSON con probabilidades (+ opcional guardado en `studies`/`predictions`).

5. **¿Qué hace PySpark aquí?**  
   Lee `csv_import_rows`, agrega por lote, escribe `csv_aggregates` y Parquet; no procesa imágenes RX.

6. **¿Es seguro para un hospital real?**  
   No en estado actual: falta certificación CE, validación clínica, DICOM, DPIA y monitorización de drift.

7. **¿Cuál es el error más peligroso del modelo?**  
   Falso negativo COVID — por eso mayor peso de clase y énfasis en recall.

8. **¿Cómo garantizáis privacidad?**  
   Roles JWT, separación paciente/imagen, no usar datos reales en demo, diseño hacia seudonimización.

9. **¿Qué automatizaciones hay?**  
   Worker CSV periódico, bucle Spark, alertas API, informe hospital, reset password por email, healthchecks Docker.

10. **¿Qué mejoraríais?**  
    CNN con datos reales, Grad-CAM, Kafka/Airflow, cluster Spark, Grafana, validación multicéntrica.

---

## 14. Checklist “domino el proyecto”

Marca cuando puedas hacerlo sin mirar notas:

- [ ] Levantar y parar Docker Compose desde `infra/docker/`
- [ ] Explicar los 3 roles y qué ve cada uno en el portal
- [ ] Hacer login y llamar un endpoint con JWT en Swagger o curl
- [ ] Describir el flujo CSV: feed → worker → API → Spark → dashboard
- [ ] Nombrar las tablas principales de PostgreSQL
- [ ] Subir una radiografía y explicar la salida de `/radiology/predict`
- [ ] Explicar preprocesado 224×224, RGB stack y aplanado para sklearn
- [ ] Definir precisión, recall, F1 y matriz de confusión
- [ ] Justificar peso mayor en clase COVID-19
- [ ] Enumerar limitaciones éticas y legales
- [ ] Señalar 3 mejoras futuras concretas
- [ ] Recorrer `docs/adr/` y citar una decisión con su alternativa descartada

---

## 15. Documentación relacionada

| Documento | Uso |
|-----------|-----|
| `docs/README.md` | Índice de toda la documentación |
| `docs/specs/` | Especificaciones SDD por módulo |
| `docs/ai-dev-diary/DIARIO_DESARROLLO_IA.md` | Entregable desarrollo con IA |
| `docs/slides/presentacion-hospital.html` | Presentación visual |

---

*Documento generado para estudio y defensa del proyecto laSalle Health Center. Última revisión alineada con el repositorio y el informe académico.*
