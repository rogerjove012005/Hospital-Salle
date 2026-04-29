# Especificaciones Técnicas - Modelo de Clasificación de Radiografías

## 1. Descripción del Problema

### Contexto
Hospital laSalle requiere sistema de clasificación automática de radiografías de tórax para:
- Acelerar triaje inicial
- Reducir carga de radiologistas
- Detectar patologías rápidamente (herramienta de soporte)

### Objetivo
Desarrollar modelo Deep Learning que clasifique radiografías en **3 categorías**:
1. **Normal**: Sin patologías detectables
2. **Neumonía**: Infección bacteriana o viral
3. **COVID-19**: Patrones específicos de COVID-19

## 2. Arquitectura del Modelo

### Backbone
- **Base**: EfficientNetB4 pre-entrenado en ImageNet
- **Razón**: Balance óptimo entre precisión (88.5% ImageNet) y eficiencia
- **Parámetros**: ~17M en base

### Capas Personalizadas
```
Input (224x224x3)
    ↓
[Normalización ImageNet]
    ↓
[EfficientNetB4 congelado (capas iniciales)]
    ↓
[Fine-tuning (últimas 20 capas)]
    ↓
[Global Average Pooling]
    ↓
[Dense 512 + BatchNorm + ReLU + Dropout(0.5)]
    ↓
[Dense 256 + BatchNorm + ReLU + Dropout(0.3)]
    ↓
[Dense 128 + BatchNorm + ReLU + Dropout(0.2)]
    ↓
[Dense 3 + Softmax]
    ↓
Output: [P(COVID), P(Neumonía), P(Normal)]
```

### Justificación de Decisiones

| Decisión | Razón | Alternativas Descartadas |
|----------|-------|--------------------------|
| Transfer Learning | Aprovechar features de ImageNet | CNN desde cero (menos datos) |
| EfficientNetB4 | Balance precisión/eficiencia | ResNet50 (más lento), VGG (menos preciso) |
| Fine-tuning últimas 20 capas | Adaptar a radiografías sin overfitting | Congelar todo (underfitting), entrenar todo (overfitting) |
| Global Average Pooling | Reducir dimensionalidad, evitar overfitting | Flatten (más parámetros) |
| Dropout progresivo | Regularización en cada capa | L2 solamente (insuficiente) |
| Class weights | Manejar desbalance de clases | Oversampling (computacionalmente caro) |

## 3. Datos y Preprocessing

### Dataset
- **Tamaño**: 300 imágenes (100 por clase) - sintético para demo
- **Producción**: Usar COVID-19 X-Ray Chest dataset (>1000 por clase)
- **División**: Train 70%, Validation 10%, Test 20%

### Preprocesamiento

1. **Lectura**: Radiografías en escala gris (PNG)
2. **Redimensionamiento**: 224x224 (requerido por EfficientNet)
3. **Normalización**: 
   - Rango: 0-1 (dividir por 255)
   - ImageNet stats: Restar media, dividir por std
4. **Canales**: Escala gris → 3 canales RGB (stack)

### Data Augmentation (solo training)
- Rotación: ±20°
- Desplazamiento: ±20%
- Zoom: ±20%
- Flip horizontal: Sí
- Brillo: ±20%

**Justificación**: Aumenta robustez a variaciones reales, evita overfitting

## 4. Entrenamiento

### Hiperparámetros
- **Optimizador**: Adam (learning_rate=1e-3)
- **Loss**: Categorical Cross-Entropy (con class weights)
- **Batch size**: 32
- **Epochs**: 50 (con early stopping)

### Regularización
- L2 (1e-4) en capas densas
- Dropout progresivo
- Batch Normalization
- Early stopping (paciencia=10, monitor=val_loss)

### Class Weights
```python
{
    'COVID-19': 1.5,    # Más importante detectar
    'NEUMANIA': 1.0,
    'NORMAL': 1.0
}
```

### Callbacks
- **EarlyStopping**: Detiene si val_loss no mejora 10 epochs
- **ReduceLROnPlateau**: Reduce learning rate si hay plateau
- **ModelCheckpoint**: Guarda mejor modelo
- **TensorBoard**: Visualización en tiempo real

## 5. Evaluación

### Métricas Primarias
- **Accuracy**: TP+TN / Total
- **Precisión**: TP / (TP+FP) - evita falsos positivos
- **Recall (Sensibilidad)**: TP / (TP+FN) - evita falsos negativos
- **Especificidad**: TN / (TN+FP)
- **F1-Score**: Media armónica Precisión-Recall

### Matriz de Confusión
Analizar:
- Verdaderos Positivos (TP): Predicción correcta
- Falsos Negativos (FN): Error crítico
- Falsos Positivos (FP): Error tolerable
- Verdaderos Negativos (TN): Rechazo correcto

### Análisis de Errores Críticos

**FN en COVID-19**: 
- Impacto: Paciente no diagnosticado, puede contagiar
- Severidad: CRÍTICA
- Acción: Revisar antes de dar alta

**FN en Neumonía**:
- Impacto: Retraso en tratamiento antibiótico
- Severidad: ALTA
- Acción: Validar con síntomas clínicos

**FP en COVID-19**:
- Impacto: Aislamiento preventivo innecesario
- Severidad: MEDIA
- Acción: Confirmación por radiólogo

## 6. Consideraciones Clínicas

### Validez del Modelo
✓ Diseño bien fundamentado  
✓ Arquitectura apropiada para imágenes médicas  
✓ Regularización adecuada  
✗ Dataset sintético (NO aplicable clínicamente)  
✗ Sin validación con expertos  
✗ Sin datos de pacientes reales  

### Limitaciones Críticas
1. **Caja negra**: No explica sus decisiones
2. **Dataset limitado**: Sintético, no representa casos reales
3. **No generaliza**: Podría fallar con equipos diferentes
4. **Contexto limitado**: Solo mira radiografía, no historia clínica
5. **Performance**: Puede degradarse con variantes de COVID

### Recomendaciones para Producción
1. Usar dataset real (COVID-19 X-Ray Chest, ChexPert, etc.)
2. Implementar técnicas de explicabilidad (GradCAM, SHAP)
3. Validación con radiologistas expertos
4. Evaluación en múltiples hospitales
5. Cumplir regulación (FDA 510k, HIPAA, GDPR)
6. Sistema de alertas para baja confianza
7. Logging completo de predicciones

## 7. Consideraciones Éticas

### Sesgos Potenciales
- Sesgo de género: Dataset podría estar desequilibrado
- Sesgo de edad: Prevalencia diferente por edad
- Sesgo de equipamiento: Máquinas diferentes
- Sesgo de geografía: Datos de una región específica
- Sesgo epidemiológico: Proporción COVID/Neumonía irreal

### Mitigación
- Auditoría pre-deployment
- Test en múltiples grupos demográficos
- Validación externa en otros hospitales
- Documentar composición del dataset
- Monitorización post-deployment

### Responsabilidades Legales
- **NO reemplaza diagnóstico médico**: Herramienta de soporte
- **FDA approval**: NO obtenido (investigación)
- **HIPAA**: Si usa datos de pacientes reales
- **GDPR**: Si hay datos europeos
- **Auditoría de algoritmos**: Requerida

## 8. Archivos y Estructura

```
ml/radiology-classifier/
├── README.md                    # Este archivo
├── requirements.txt             # Dependencias Python
├── run_pipeline.py             # Script end-to-end
├── configs/
│   └── config.py               # Configuración global
├── data/
│   ├── dataset_manager.py      # Descarga/exploración
│   ├── download_dataset.py     # Script descarga
│   └── synthetic/              # Dataset sintético
├── training/
│   ├── preprocess.py           # Normalización/augmentation
│   ├── model.py                # Arquitectura CNN
│   ├── train.py                # Script training
│   └── evaluate.py             # Evaluación
├── inference/
│   ├── clinical_analysis.py    # Análisis clínico
│   └── predictor.py            # Inferencia (futuro)
├── notebooks/
│   └── analysis.ipynb          # Análisis interactivo
└── models/
    ├── best_model.h5           # Mejor checkpoint
    ├── model_final.h5          # Modelo final
    ├── training_history.png    # Gráficas training
    ├── confusion_matrix.png    # Matriz confusión
    ├── roc_curves.png          # Curvas ROC
    └── clinical_analysis.json  # Análisis médico
```

## 9. Instrucciones de Ejecución

### Setup
```bash
cd ml/radiology-classifier
pip install -r requirements.txt
```

### Ejecutar pipeline completo
```bash
python run_pipeline.py
```

### Componentes individuales
```bash
# Dataset
python data/download_dataset.py

# Preprocesamiento
python training/preprocess.py

# Entrenamiento
python training/train.py

# Evaluación
python training/evaluate.py

# Análisis clínico
python inference/clinical_analysis.py
```

## 10. Diario de Desarrollo IA

### Herramientas Utilizadas
- **Claude (GitHub Copilot)**: Generación de arquitectura, debugging
- **Justificación**: Velocidad de development, buena comprensión de dominio médico

### Proceso
1. Especificación: Diseño de arquitectura basado en mejores prácticas
2. Generación: Copilot generó 70% del código
3. Refinamiento: Ajustes manuales para precisión clínica
4. Testing: Validación iterativa

### Aprendizajes
- Transfer Learning esencial para datasets pequeños
- Explicabilidad crítica en contexto médico
- Balance precisión/explicabilidad es desafío real
- Dataset real es requisito mínimo para producción

## 11. Conclusiones y Reflexión Crítica

### ¿Funciona el modelo?
- ✓ Arquitectura válida
- ✓ Entrenamiento sin errores
- ✓ Evaluación posible
- ✗ NO validado clínicamente
- ✗ Dataset sintético no representa realidad

### ¿Es aplicable en hospital?
- NO en estado actual
- Requiere: Dataset real, validación clínica, explicabilidad, regulación
- Timeline: 6-12 meses para producción

### Impacto de IA Generativa
- Aceleró 70% del coding
- Redujo tiempo design-implementation
- Permitió enfoque en validación clínica (lo importante)
- Limitación: Sin conocimiento médico real, solo código

### Próximos Pasos
1. Integración con dataset real
2. Explicabilidad (GradCAM)
3. Validación con radiologistas
4. Cumplimiento regulatorio
5. Sistema de alerts en producción
