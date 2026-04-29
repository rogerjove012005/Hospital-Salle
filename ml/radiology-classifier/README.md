# Clasificador de Radiografías - Modelo de Deep Learning

## Descripción
Modelo CNN para clasificación de radiografías de tórax en tres categorías:
- **Sana**: Sin patologías detectables
- **Neumonía**: Infección bacteriana o viral estándar
- **COVID-19**: Patrones específicos asociados a COVID-19

## Estructura del proyecto

```
ml/radiology-classifier/
├── data/                    # Datasets
├── configs/                 # Configuraciones
├── training/                # Scripts de entrenamiento
├── inference/               # Scripts de inferencia
├── notebooks/               # Jupyter notebooks para análisis
└── requirements.txt         # Dependencias
```

## Uso

1. Instalar dependencias: `pip install -r requirements.txt`
2. Descargar dataset: `python data/download_dataset.py`
3. Preparar datos: `python data/prepare_data.py`
4. Entrenar modelo: `python training/train.py`
5. Evaluar: `python training/evaluate.py`

## Investigación y Decisiones Técnicas

### Arquitectura del Modelo
- CNN con TransferLearning usando EfficientNetB4 pre-entrenado en ImageNet
- Razón: Balance óptimo entre precisión y eficiencia computacional
- Capas personalizadas para adaptarse a nuestras 3 clases

### Tratamiento de Datos
- Redimensionamiento a 224x224 (tamaño estándar para EfficientNet)
- Normalización: ImageNet statistics
- Data augmentation para balance de clases

### Evaluación Clínica
- Focus en matriz de confusión para errores críticos (falsos negativos en COVID)
- Análisis de sensibilidad vs especificidad
- Justificación médica de las decisiones tomadas

## Consideraciones Éticas

- Sesgo en dataset: Se documentará la representatividad del dataset
- Falsos negativos críticos: Especialmente importantes en COVID-19
- Limitaciones del modelo: No reemplaza diagnóstico médico profesional
- Privacidad: Uso de datos sintéticos/públicos solo
