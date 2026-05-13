# laSalle Health Center — Sistema Inteligente de Soporte Hospitalario

Plataforma hospitalaria que combina una **API REST con autenticación por roles**, un **portal web** para pacientes y personal clínico, y un **clasificador de radiografías** basado en redes neuronales convolucionales (CNN). Todo corre containerizado con Docker Compose.

---

## Qué hace el sistema

| Módulo | Descripción |
|--------|-------------|
| **Portal web** | Login, registro y gestión de expedientes para pacientes, médicos y administradores |
| **API REST** | FastAPI con JWT, control de roles (admin / médico / paciente) y acceso a BBDD |
| **Clasificador IA** | CNN (EfficientNetB4 + TensorFlow) que clasifica radiografías de tórax en: **Sana**, **Neumonía** o **COVID-19** |
| **Almacenamiento** | MinIO (compatible S3) para imágenes de radiografías |
| **Base de datos** | PostgreSQL con esquema de pacientes, médicos y estudios radiológicos |
| **Correo (dev)** | Mailpit — bandeja de pruebas para recuperación de contraseña sin SMTP real |

---

## Requisitos previos

- **Docker Desktop** (o Docker Engine + Compose v2) — [descargar](https://docs.docker.com/get-docker/)
- **Python 3.10+** — solo si quieres ejecutar el módulo ML de forma local

Comprueba que Docker está activo:

```bash
docker --version
docker compose version
```

---

## Inicio rápido — plataforma web (5 minutos)

```bash
# 1. Clona el repositorio
git clone <url-del-repo>
cd Hospital-Salle

# 2. Copia el fichero de configuración (los valores por defecto funcionan en local)
cp infra/docker/.env.example infra/docker/.env

# 3. Levanta todos los servicios
cd infra/docker
docker compose --env-file .env up --build
```

Espera a que aparezca `api | Application startup complete.` en los logs (suele tardar ~60 s la primera vez mientras descarga imágenes y compila).

### URLs de acceso

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Portal web** | http://localhost:3000 | Interfaz principal |
| **API docs** | http://localhost:8000/docs | Swagger UI interactivo |
| **Mailpit** (correo dev) | http://localhost:8025 | Bandeja de pruebas para "olvidé contraseña" |
| **pgAdmin** | http://localhost:5050 | Administración visual de PostgreSQL |
| **MinIO** | http://localhost:9001 | Consola de almacenamiento de objetos |

### Credenciales por defecto

| Recurso | Usuario / Email | Contraseña |
|---------|-----------------|------------|
| Portal / API (admin) | `rogerjove012005@gmail.com` | `hospital` |
| pgAdmin | `admin@admin.com` | `admin` |
| MinIO | `minioadmin` | `minioadmin` |

> Para conectar pgAdmin al servidor PostgreSQL usa host `postgres`, puerto `5432`, usuario `hospital`, contraseña `hospital`, BBDD `hospital`.

### Parar los servicios

```bash
docker compose --env-file .env down          # para y elimina contenedores
docker compose --env-file .env down -v       # también borra los volúmenes (datos)
```

---

## Roles del sistema

El portal distingue tres perfiles. El administrador puede crear usuarios; pacientes y médicos pueden auto-registrarse.

| Rol | Qué puede hacer |
|-----|-----------------|
| `admin` | Ver y crear usuarios, listar todos los pacientes y estudios |
| `medico` | Ver todos los pacientes y sus estudios radiológicos |
| `paciente` | Ver su propio expediente y sus estudios |

---

## Módulo de IA — Clasificador de radiografías

El módulo ML funciona de forma independiente al Docker; se ejecuta en local con Python.

### Instalación

```bash
cd ml/radiology-classifier
pip install -r requirements.txt
```

> En macOS usa `pip3` si `pip` apunta a Python 2.

### Ejecutar el pipeline completo

```bash
# Desde ml/radiology-classifier/
python run_pipeline.py
```

El pipeline realiza 5 pasos automáticamente:

1. **Dataset** — genera imágenes sintéticas (100 por clase: NORMAL, NEUMONÍA, COVID-19)
2. **Preprocesado** — redimensiona a 224×224, normaliza y aplica data augmentation
3. **Entrenamiento** — CNN con EfficientNetB4 preentrenada en ImageNet
4. **Evaluación** — matriz de confusión, curvas ROC, métricas por clase
5. **Análisis clínico** — informe con sensibilidad/especificidad y falsos negativos críticos

### Archivos generados tras el pipeline

```
ml/radiology-classifier/
├── data/synthetic/              # imágenes sintéticas (NORMAL / NEUMONIA / COVID-19)
├── data/dataset_samples.png     # muestras visuales del dataset
├── data/augmentation_examples.png
└── ml/radiology-classifier/models/
    ├── model_final.pkl          # modelo entrenado
    ├── training_history.png     # curvas de entrenamiento
    ├── confusion_matrix.png     # matriz de confusión
    ├── roc_curves.png           # curvas ROC por clase
    ├── evaluation_report.json   # métricas numéricas
    └── clinical_analysis.json   # informe clínico
```

---

## Estructura del proyecto

```
.
├── infra/
│   ├── docker/
│   │   ├── docker-compose.yml  # orquestación de todos los servicios
│   │   └── .env.example        # variables de entorno (copia a .env)
│   └── db/
│       └── 01-init.sql         # esquema inicial de PostgreSQL
├── ml/
│   └── radiology-classifier/
│       ├── run_pipeline.py     # punto de entrada del pipeline ML
│       ├── training/           # entrenamiento, preprocesado, evaluación
│       ├── inference/          # análisis clínico post-evaluación
│       ├── data/               # dataset manager e imágenes sintéticas
│       ├── configs/            # hiperparámetros y configuración
│       └── requirements.txt
├── services/
│   ├── api/                    # FastAPI (auth, pacientes, estudios)
│   │   └── app/
│   │       ├── main.py         # rutas y startup
│   │       ├── auth.py         # JWT, roles, registro, reset password
│   │       ├── db.py           # conexión SQLAlchemy
│   │       └── security.py     # hashing de contraseñas
│   └── frontend/               # portal web estático (nginx)
│       └── public/
│           ├── index.html      # login / registro
│           ├── landing.html    # dashboard del usuario autenticado
│           └── app.js          # lógica del portal
├── docs/                       # ADRs, ética, diario IA, specs
├── automation/                 # alertas, informes, movimiento de ficheros
├── pipelines/                  # ingestión, procesado, calidad, orquestación
└── data/                       # datos raw / staging / processed / warehouse
```

---

## Variables de entorno relevantes

Todas están en `infra/docker/.env` (copia de `.env.example`). Las más importantes:

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `ADMIN_EMAIL` | `rogerjove012005@gmail.com` | Email del admin inicial |
| `ADMIN_PASSWORD` | `hospital` | Contraseña del admin inicial |
| `JWT_SECRET` | `dev-only-change-me` | Secreto para firmar tokens JWT (**cambiar en producción**) |
| `POSTGRES_PASSWORD` | `hospital` | Contraseña de PostgreSQL |
| `SMTP_HOST` | `mailpit` | Servidor de correo (en dev usa Mailpit) |
| `FRONTEND_PORT` | `3000` | Puerto del portal web |
| `API_PORT` | `8000` | Puerto de la API |

Para usar Gmail en lugar de Mailpit, edita `.env`:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_correo@gmail.com
SMTP_PASSWORD=contraseña_de_aplicación
SMTP_USE_STARTTLS=1
```

---

## API — Endpoints principales

La documentación interactiva completa está en http://localhost:8000/docs

| Método | Ruta | Acceso | Descripción |
|--------|------|--------|-------------|
| `GET` | `/health` | público | Estado de la API |
| `POST` | `/auth/login` | público | Login → devuelve JWT |
| `POST` | `/auth/register` | público | Auto-registro (paciente/médico) |
| `POST` | `/auth/forgot-password` | público | Solicitar reset de contraseña |
| `GET` | `/auth/me` | autenticado | Perfil del usuario actual |
| `GET` | `/patients` | admin, médico | Lista de pacientes |
| `GET` | `/patients/me` | paciente | Mi expediente |
| `GET` | `/studies` | admin, médico | Todos los estudios radiológicos |
| `GET` | `/studies/me` | paciente | Mis estudios |
| `POST` | `/admin/users` | admin | Crear usuario manualmente |

---

## Aviso

> Proyecto académico desarrollado en La Salle – Universitat Ramon Llull. Los datos son sintéticos o públicos y no tienen valor clínico real. El modelo de IA **no reemplaza el diagnóstico médico profesional**.
