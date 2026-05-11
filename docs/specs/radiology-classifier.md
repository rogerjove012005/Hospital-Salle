# Especificación (SDD): clasificador radiológico — triple clase

## 1. Descripción funcional

Módulo de **apoyo al triaje** que recibe una **radiografía de tórax** (imagen PNG/JPEG) y devuelve una **clasificación en tres clases** alineada con el encargo académico:

| Clase en API / modelo | Significado clínico (encargo) |
|----------------------|--------------------------------|
| **SANA** | Tórax sin patrones sugestivos de las patologías objetivo en este ejercicio. |
| **NEUMONIA** | Patrones compatibles con consolidación / infección estándar (ejercicio académico). |
| **COVID-19** | Patrones asociados en el enunciado a COVID-19 (datos sintéticos o proxy visual). |

El resultado es **probabilístico** y lleva **disclaimer** explícito: no constituye diagnóstico médico ni sustituye al radiólogo.

## 2. Inputs y outputs

### 2.1 Entrenamiento / evaluación (offline)

| Tipo | Descripción |
|------|-------------|
| **Entrada** | PNG en `ml/radiology-classifier/data/synthetic/{SANA,NEUMONIA,COVID-19}/` generados por `scripts/generate_synthetic_radiology.py`. |
| **Salida** | `models/model_final.pkl`, `class_names.json`, `evaluation_report.json`, `confusion_matrix.png`, `roc_curves.png`, `clinical_analysis.json`, `training_history.png`. |

### 2.2 Inferencia (API)

| Endpoint | Entrada | Salida |
|----------|---------|--------|
| `POST /radiology/predict` | `multipart/form-data`, campo `file` (PNG/JPEG), máx. 8 MB. | JSON: clase predicha, índice, mapa de probabilidades por etiqueta, `disclaimer`. |
| `GET /radiology/metrics` | JWT; roles `admin` o `medico`. | JSON: `available`, `accuracy` (si hay `evaluation_report.json`), `class_names`, ruta lógica del informe. |

### 2.3 Frontend

| Ruta | Comportamiento |
|------|----------------|
| `/radiology.html` | Tras login: muestra métricas (`/radiology/metrics`) y permite subir imagen para `/radiology/predict`. Enlace desde el panel (`landing.html`) para roles admin/médico. |

## 3. Restricciones técnicas y de negocio

- **Datos**: en el repo por defecto se usan **imágenes sintéticas** (no pacientes reales) para cumplir privacidad y reproducibilidad en aulas.
- **Rendimiento**: el build Docker de la API ejecuta `bootstrap_model.py` en la etapa de imagen para empaquetar artefactos; el tiempo de build aumenta (~1–2 min).
- **Seguridad**: predicción solo con **JWT** válido y rol autorizado.
- **Negocio**: el hospital (simulación) solo usa la salida como **soporte**; la decisión clínica queda documentada como responsabilidad humana.

## 4. Tratamiento de datos (preprocesado)

- Escala de grises → redimensionado **224×224** → normalización **[0,1]** → **tres canales** repetidos (compatibilidad con pipeline numérico de features).
- División **estratificada** train / validación / test (`training/preprocess.py`).
- **Data augmentation** opcional documentada en preprocesado (rotación, flip, brillo) para robustez en datasets pequeños.

## 5. Modelo e integración con el resto del sistema

- **Implementación actual**: pipeline **scikit-learn** `StandardScaler` → `PCA` → `MLPClassifier` (ver ADR `docs/adr/0003-radiology-sklearn-baseline.md`). Cumple el encargo de **clasificación supervisada** y análisis de errores; la asignatura cita **Deep Learning** como orientación de investigación: la hoja de ruta hacia CNN / transfer learning está documentada en `ml/radiology-classifier/README.md`.
- **Integración**:
  - Artefactos embebidos en contenedor **API** (`services/api/Dockerfile` multi-stage → `/app/models/radiology/`).
  - El almacenamiento de **estudios** con imagen en **MinIO** y metadatos en **PostgreSQL** existe en el esquema global del proyecto; la predicción actual opera sobre **upload directo**. La extensión natural es persistir predicciones ligadas a `studies` (fuera del alcance mínimo actual, descrito en `docs/architecture/radiology-integration.md`).

## 6. Evaluación y criterio clínico (“el porqué”)

- **Matriz de confusión** (absoluta y normalizada por fila) y **curvas ROC** por clase.
- **Análisis de falsos negativos** por nombre de clase (no por índice fijo): especialmente **COVID-19** y **NEUMONIA**.
- **`clinical_analysis.json`**: razonamiento clínico, riesgos de FN/FP, limitaciones, ética y recomendaciones (ver también `docs/ethics/radiology-ia-etica.md`).

## 7. Criterios de aceptación

1. Tres clases estables **SANA**, **NEUMONIA**, **COVID-19** en config, entrenamiento y API.
2. Script reproducible de dataset sintético + bootstrap de entrenamiento/evaluación.
3. API con **métricas** y **predicción** documentadas y probables desde `radiology.html`.
4. Imagen API construida con **Compose** desde monorepo (`context: ../..`, `dockerfile: services/api/Dockerfile`).
5. Documentación SDD + ética + ADR + integración enlazada desde README.

## 8. Referencias en código

| Ruta | Rol |
|------|-----|
| `ml/radiology-classifier/scripts/generate_synthetic_radiology.py` | Datos sintéticos |
| `ml/radiology-classifier/scripts/bootstrap_model.py` | Pipeline offline completo |
| `services/api/app/radiology.py` | Router FastAPI |
| `services/frontend/public/radiology.html` | UI |

## 9. Documentación relacionada

- **Decisión de modelo (baseline vs CNN):** [`docs/adr/0003-radiology-sklearn-baseline.md`](../adr/0003-radiology-sklearn-baseline.md)
- **Ética y privacidad:** [`docs/ethics/radiology-ia-etica.md`](../ethics/radiology-ia-etica.md)
- **Integración con estudios / MinIO:** [`docs/architecture/radiology-integration.md`](../architecture/radiology-integration.md)
- **Diario IA (obligatorio):** [`docs/ai-dev-diary/2026-05-radiografia-ia.md`](../ai-dev-diary/2026-05-radiografia-ia.md)
