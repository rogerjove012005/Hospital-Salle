# Sistema Inteligente de Soporte Hospitalario

Repositorio base para estructurar el proyecto del **laSalle Health Center** (IA + Big Data + automatización + visualización + despliegue containerizado).

## Estructura de carpetas (GitHub)

> Objetivo: que el repo sea **fácil de navegar** por “features” del enunciado (modelo IA, pipeline, automatización, dashboard, infraestructura y documentación).

```
.
├── Enunciado-Hospital.pdf
├── README.md
├── automation/
│   ├── alerts/                 # alertas ante eventos/fallos (simuladas: log/email/dashboard)
│   ├── reports/                # generación automática de informes
│   └── file-mover/             # organización/movimiento de ficheros (ingesta, archivado, etc.)
├── data/
│   ├── external/               # datasets descargados (idealmente NO versionar; documentar origen)
│   ├── raw/                    # datos “en crudo” (CSV/JSON/logs/imágenes)
│   ├── staging/                # datos intermedios tras validación/normalización
│   ├── processed/              # datos transformados listos para consumo
│   ├── warehouse/              # salida estilo DWH/lakehouse (tablas/particiones)
│   └── models/                 # artefactos de modelos (pesos, métricas, configs)
├── docs/
│   ├── specs/                  # SDD: especificaciones por módulo (inputs/outputs/AC)
│   ├── architecture/           # diagramas + explicación del flujo end-to-end
│   ├── adr/                    # decisiones técnicas (Architecture Decision Records)
│   ├── ethics/                 # análisis ético/legal (sesgos, privacidad, riesgos, límites)
│   ├── ai-dev-diary/           # diario de desarrollo con IA (prompts, iteraciones, reflexiones)
│   └── slides/                 # presentación (10–15 min)
├── infra/
│   ├── docker/                 # docker-compose, Dockerfiles, .env.example
│   ├── db/                     # init scripts / esquemas / seeds para bases de datos
│   └── observability/          # logging/monitorización (configuración básica)
├── ml/
│   └── radiology-classifier/   # módulo DL radiografías (Sana/Neumonía/COVID-19)
│       ├── training/           # entrenamiento (scripts, dataloaders, métricas, confusión)
│       ├── inference/          # inferencia/serving (batch u online)
│       ├── notebooks/          # exploración (EDA imágenes, pruebas rápidas)
│       └── configs/            # configs (hiperparámetros, rutas, labels)
├── notebooks/                  # notebooks generales (pipeline, análisis, prototipos)
├── pipelines/
│   ├── ingestion/              # ingesta (watch folder, API simulada, conectores)
│   ├── processing/             # procesamiento escalable (Spark/Dask/Beam)
│   ├── quality/                # validación de calidad (duplicados, nulos, corruptos)
│   └── orchestration/          # orquestación (schedules, DAGs, triggers)
├── scripts/                    # utilidades de dev (setup, lint, dataset download)
├── services/
│   ├── api/                    # API REST (exponer datos procesados + predicciones)
│   └── dashboard/              # dashboard (métricas, gráficos, estado del pipeline)
└── tests/                      # tests unit/integration (pipeline, API, ML)
```

## Cómo se relaciona con los “features” del enunciado

- **Modelo de IA (clínico)**: `ml/` (especialmente `ml/radiology-classifier/`).
- **Procesamiento de datos / Big Data (pipeline)**: `pipelines/` + `data/`.
- **Automatización**: `automation/` (informes, alertas, movimiento de ficheros).
- **Visualización**: `services/dashboard/` + (opcional) informes en `automation/reports/`.
- **Infra Big Data / despliegue**: `infra/docker/` (Docker + Compose, volúmenes, env).
- **Monitorización y calidad**: `infra/observability/` + `pipelines/quality/`.
- **SDD + diario IA (entregables)**: `docs/specs/` + `docs/ai-dev-diary/`.
- **Memoria técnica / ética-legal / justificaciones**: `docs/architecture/`, `docs/adr/`, `docs/ethics/`.

## Convención recomendada para GitHub

- Cada módulo importante tiene su **SPEC** antes de código:
  - `docs/specs/<modulo>.md` con:
    - descripción funcional
    - inputs/outputs
    - restricciones técnicas/negocio
    - criterios de aceptación
- Cada decisión relevante queda registrada como ADR:
  - `docs/adr/0001-<decision>.md`
- **Radiografía (clasificación RX)**: desarrollo y PRs desde la rama **`feature/radiografia-rx`** (API `/radiology/*`, UI `/radiology.html`, build multi-stage en `services/api/Dockerfile`).

## Encargo académico — bloque «Radiografía» (trazabilidad)

| Requisito del enunciado | Dónde se cubre en el repo |
|-------------------------|---------------------------|
| Clasificación triple Sana / Neumonía / COVID-19 | `ml/radiology-classifier/` (`SANA`, `NEUMONIA`, `COVID-19`), SDD [`docs/specs/radiology-classifier.md`](docs/specs/radiology-classifier.md) |
| Investigación y justificación técnica | `ml/radiology-classifier/README.md`, ADR [`docs/adr/0003-radiology-sklearn-baseline.md`](docs/adr/0003-radiology-sklearn-baseline.md) |
| Tratamiento de datos (preprocesado, splits) | `training/preprocess.py`, datos sintéticos `scripts/generate_synthetic_radiology.py` |
| Evaluación + matriz de confusión + criterio clínico | `training/evaluate.py`, `inference/clinical_analysis.py` → artefactos en build API |
| Integración (API + Docker) | `services/api/app/radiology.py`, `services/api/Dockerfile`, Compose monorepo |
| Visualización | `services/frontend/public/radiology.html` |
| Ética y riesgos | [`docs/ethics/radiology-ia-etica.md`](docs/ethics/radiology-ia-etica.md) |
| Diario IA (obligatorio) | [`docs/ai-dev-diary/2026-05-radiografia-ia.md`](docs/ai-dev-diary/2026-05-radiografia-ia.md) |

## Datos (CSV)

El fichero `hospital_dataset.xlsx` (proyecto) puede convertirse a CSV (por defecto se escribe bajo `data/raw/`, carpetas ignoradas por Git según `.gitignore`):

```bash
python3 scripts/xlsx_to_csv.py hospital_dataset.xlsx data/raw/hospital_dataset.csv
```

Requisitos: `pip install pandas openpyxl`.

## Ejecución (`docker compose`)

```bash
cd infra/docker
docker compose --env-file .env.example up --build
```

Servicios principales incluidos en Compose:

| Servicio | Función breve |
|----------|----------------|
| postgres / minio / mailpit | Persistencia relacional + objetos + correo dev |
| api | REST (auth, `/imports/csv*`, **`/radiology/metrics`** y **`/radiology/predict`**, otros) |
| frontend | Portal nginx + estáticos (`/imports.html`, **`/radiology.html`**, landing) |
| **mock-hospital-feed** | nginx que sirve un CSV ejemplo (simula API/sistema legacy) |
| **csv-ingest-worker** | Ingesta **automatizada**: descarga esa URL (+ otras en `CSV_PULL_URLS`) y vigila `./csv-ingest-mounts/inbox/*.csv`; mueve resultado a `processed/` o `failed/` |
| **spark-csv-aggregate** | **PySpark** `local[*]`: agregaciones por lote desde `csv_import_rows` → tablas `csv_spark_*` + Parquet bajo `./spark-processed-output/` |

Tras ingestar datos, el API expone **`GET /stats/csv-aggregates`** (JWT) con el último snapshot agregado y **`GET /health/pipeline`** (sin JWT) para comprobar rápido fecha y totales del último job. Los eventos `spark_csv_aggregate` aparecen en **`GET /admin/imports/pipeline-events`**. Flujo dibujado en [`docs/architecture/pipeline-dataflow.md`](docs/architecture/pipeline-dataflow.md).

Para probar sólo vigilancia carpeta sin feed HTTP:

```bash
CSV_PULL_URLS= docker compose --env-file .env.example up -d csv-ingest-worker
```

(SD completa del worker: [`docs/specs/automated-csv-ingestion.md`](docs/specs/automated-csv-ingestion.md). Job Spark: [`docs/specs/pyspark-csv-aggregates.md`](docs/specs/pyspark-csv-aggregates.md).)

Colocad el `docker-compose.yml` y los Dockerfiles en `infra/docker/` y documentad aquí:

- Servicios esperados (ejemplo histórico):
  - base de datos estructurada (PostgreSQL ✓)
  - almacenamiento objetos (MinIO ✓)
  - procesamiento **PySpark** (contenedor `spark-csv-aggregate` ✓, modo cluster opcional fuera del alcance docente)
  - API (FastAPI ✓)
  - dashboard frontend estático ✓

## Notas

- `data/` contiene carpetas para datos, pero **no es recomendable** versionar datasets pesados en Git. Mejor: documentar fuentes en `docs/` y usar `scripts/` para descargarlos/prepararlos.

