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

## Datos (CSV)

El fichero `hospital_dataset.xlsx` (proyecto) puede convertirse a CSV (por defecto se escribe bajo `data/raw/`, carpetas ignoradas por Git según `.gitignore`):

```bash
python3 scripts/xlsx_to_csv.py hospital_dataset.xlsx data/raw/hospital_dataset.csv
```

Requisitos: `pip install pandas openpyxl`.

## Ejecución (placeholder)

Cuando añadáis los contenedores, la idea es poder levantarlo con un comando:

```bash
cd infra/docker
docker compose --env-file .env.example up --build
```

Colocad el `docker-compose.yml` y los Dockerfiles en `infra/docker/` y documentad aquí:

- Servicios esperados (ejemplo):
  - base de datos estructurada (p. ej. PostgreSQL)
  - almacenamiento objetos (p. ej. MinIO/S3) para imágenes
  - procesamiento (Spark/Dask)
  - API (FastAPI/Flask)
  - dashboard (Streamlit/Grafana/etc.)

## Notas

- `data/` contiene carpetas para datos, pero **no es recomendable** versionar datasets pesados en Git. Mejor: documentar fuentes en `docs/` y usar `scripts/` para descargarlos/prepararlos.

