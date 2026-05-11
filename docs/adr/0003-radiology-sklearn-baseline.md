# ADR 0003: Baseline sklearn (PCA + MLP) para clasificación radiológica triple

## Estado

Aceptado (proyecto académico, iteración 1).

## Contexto

El encargo exige:

- Clasificación triple **Sana / Neumonía / COVID-19**.
- Investigación y justificación técnica, evaluación con **matriz de confusión** y reflexión clínica.
- Integración con **API** e infraestructura **Docker**.

El enunciado orienta hacia **Deep Learning** en imágenes; el repositorio debe ser **reproducible en CPU** en aulas y en `docker compose` sin GPU obligatoria.

## Decisión

Usar un pipeline **scikit-learn**:

`StandardScaler` → `PCA` (reducción de dimensionalidad) → `MLPClassifier` (red neuronal feed-forward sobre componentes principales).

Los datos de entrenamiento por defecto son **sintéticos** (script), con pesos de muestra para no infravalorizar **COVID-19** y **NEUMONIA**.

## Consecuencias

### Positivas

- Entrenamiento rápido en CPU; encaja en **multi-stage build** de la imagen API.
- Métricas y **matriz de confusión** interpretables con el mismo stack (`sklearn`, `matplotlib`, `seaborn`).
- Código compacto y fácil de auditar para la memoria técnica.

### Negativas / riesgos

- **No** explota convoluciones espaciales: peor capacidad de generalización en radiografías reales frente a una **CNN**.
- PCA es **lineal**: patrones sutiles de opacidades pueden no separarse bien.
- El encargo menciona explícitamente DL: debe documentarse esta decisión como **baseline** y plan de evolución (ver `ml/radiology-classifier/README.md`).

## Alternativas consideradas

| Alternativa | Motivo de descarte / aplazamiento |
|-------------|-------------------------------------|
| EfficientNet / ResNet fine-tuned | Requiere GPU razonable, más dependencias (TF/torch), tiempos de build mayores en CI docente. |
| CNN pequeña desde cero | Riesgo de overfitting extremo con N pequeño sin transfer. |
| **SVM** sobre features PCA | Menos flexible que MLP en fronteras no lineales complejas. |

## Próximos pasos sugeridos

1. Congelar baseline y métricas en memoria técnica.
2. Rama experimental `feature/rx-cnn` con PyTorch + EfficientNet-B0 y mismo contrato API.
3. Validação externa y sesgo por sexo/edad si se dispone de metadatos.
