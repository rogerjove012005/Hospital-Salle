"""
Arquitectura del modelo CNN para clasificación de radiografías
Utiliza EfficientNetB4 pre-entrenado con transferencia de aprendizaje
"""

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models
from tensorflow.keras.applications import EfficientNetB4
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import (
    EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
)
import numpy as np


class RadiologyModel:
    """Constructor del modelo de clasificación"""
    
    def __init__(self, num_classes=3, img_size=224):
        self.num_classes = num_classes
        self.img_size = img_size
        self.model = None
    
    def build_transfer_learning_model(self, trainable_layers=20):
        """
        Construye modelo con Transfer Learning usando EfficientNetB4
        
        JUSTIFICACIÓN DE LA ARQUITECTURA:
        - EfficientNetB4: Balance óptimo entre precisión y eficiencia
        - Pre-entrenado en ImageNet: Capta features generales de imágenes
        - Fine-tuning: Adapta features a radiografías específicas
        - Capas personalizadas: Aprende patrones médicos específicos
        """
        
        # Cargar modelo pre-entrenado (sin capas fully connected)
        base_model = EfficientNetB4(
            input_shape=(self.img_size, self.img_size, 3),
            include_top=False,
            weights='imagenet'
        )
        
        # Congelar capas iniciales (features generales)
        # Fine-tune solo las últimas capas (features específicas médicas)
        for layer in base_model.layers[:-trainable_layers]:
            layer.trainable = False
        
        # Descongelar últimas capas
        for layer in base_model.layers[-trainable_layers:]:
            layer.trainable = True
        
        # Construir modelo completo
        model = models.Sequential([
            # Input
            layers.Input(shape=(self.img_size, self.img_size, 3)),
            
            # Normalización
            layers.Lambda(self._normalize_imagenet),
            
            # Base pre-entrenada
            base_model,
            
            # Global Average Pooling
            layers.GlobalAveragePooling2D(),
            
            # Capas densas personalizadas
            layers.Dense(512, activation='relu', 
                        kernel_regularizer=keras.regularizers.l2(1e-4)),
            layers.BatchNormalization(),
            layers.Dropout(0.5),
            
            layers.Dense(256, activation='relu',
                        kernel_regularizer=keras.regularizers.l2(1e-4)),
            layers.BatchNormalization(),
            layers.Dropout(0.3),
            
            layers.Dense(128, activation='relu',
                        kernel_regularizer=keras.regularizers.l2(1e-4)),
            layers.BatchNormalization(),
            layers.Dropout(0.2),
            
            # Output
            layers.Dense(self.num_classes, activation='softmax')
        ])
        
        self.model = model
        self._log_architecture_decisions()
        
        return model
    
    def _normalize_imagenet(self, x):
        """Normaliza según estadísticas de ImageNet"""
        mean = tf.constant([0.485, 0.456, 0.406])
        std = tf.constant([0.229, 0.224, 0.225])
        return (x - mean) / std
    
    def compile_model(self, learning_rate=1e-3):
        """Compila el modelo con loss y optimizador"""
        
        # Usar weighted loss para manejar desbalance de clases
        # En radiografías, los falsos negativos en COVID son críticos
        class_weights = {
            0: 1.5,  # COVID-19: más importante detectar
            1: 1.0,  # Neumonía
            2: 1.0   # Normal
        }
        
        optimizer = Adam(learning_rate=learning_rate)
        
        # Loss: categorical cross-entropy con class weights
        loss = keras.losses.CategoricalCrossentropy()
        
        # Métricas
        metrics = [
            keras.metrics.CategoricalAccuracy(name='accuracy'),
            keras.metrics.Precision(name='precision'),
            keras.metrics.Recall(name='recall'),
            keras.metrics.AUC(name='auc')
        ]
        
        self.model.compile(
            optimizer=optimizer,
            loss=loss,
            metrics=metrics
        )
        
        return self.model, class_weights
    
    def get_callbacks(self, checkpoint_dir='ml/radiology-classifier/models'):
        """Crea callbacks para entrenamiento"""
        
        callbacks = [
            # Early stopping para evitar overfitting
            EarlyStopping(
                monitor='val_loss',
                patience=10,
                restore_best_weights=True,
                verbose=1
            ),
            
            # Reducir learning rate si no hay mejora
            ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=1e-6,
                verbose=1
            ),
            
            # Guardar mejor modelo
            ModelCheckpoint(
                f'{checkpoint_dir}/best_model.h5',
                monitor='val_accuracy',
                save_best_only=True,
                verbose=0
            ),
            
            # TensorBoard
            keras.callbacks.TensorBoard(
                log_dir=f'{checkpoint_dir}/logs',
                histogram_freq=1,
                write_graph=True
            )
        ]
        
        return callbacks
    
    def _log_architecture_decisions(self):
        """Documenta decisiones de arquitectura"""
        print("\n" + "="*60)
        print("ARQUITECTURA DEL MODELO")
        print("="*60)
        
        print(f"\n🏗️ BACKBONE:")
        print(f"  • Modelo: EfficientNetB4")
        print(f"  • Pre-entrenamiento: ImageNet")
        print(f"  • Parámetros base: ~17M")
        
        print(f"\n🔧 CONFIGURACIÓN:")
        print(f"  • Capas congeladas: Primeras capas (features generales)")
        print(f"  • Capas trainables: Últimas 20 capas (features médicas)")
        print(f"  • Global Average Pooling: Reduce dimensionalidad")
        
        print(f"\n📊 CAPAS PERSONALIZADAS:")
        print(f"  • Dense 512 + BatchNorm + Dropout(0.5)")
        print(f"  • Dense 256 + BatchNorm + Dropout(0.3)")
        print(f"  • Dense 128 + BatchNorm + Dropout(0.2)")
        print(f"  • Dense 3 + Softmax (output)")
        
        print(f"\n✓ JUSTIFICACIÓN:")
        print(f"  • Transfer Learning: Aprovechar conocimiento de ImageNet")
        print(f"  • EfficientNet: Mejor balance precisión/eficiencia")
        print(f"  • Regularización L2: Prevenir overfitting")
        print(f"  • Dropout progresivo: Regularización adicional")
        print(f"  • Batch Normalization: Estabilidad del entrenamiento")
        
        print(f"\n⚠️  CONSIDERACIONES MÉDICAS:")
        print(f"  • Transfer Learning desde ImageNet podría introducir sesgos")
        print(f"  • Fine-tuning permite adaptación a radiografías")
        print(f"  • Capas densas capturan interacciones complejas")
        
        self.model.summary()
    
    def get_model(self):
        """Retorna el modelo compilado"""
        return self.model


def create_model(num_classes=3, img_size=224, learning_rate=1e-3):
    """Función helper para crear el modelo"""
    
    print("Construyendo modelo...")
    
    builder = RadiologyModel(num_classes, img_size)
    model = builder.build_transfer_learning_model()
    model, class_weights = builder.compile_model(learning_rate)
    
    return model, builder, class_weights


if __name__ == '__main__':
    # Prueba de construcción
    model, builder, class_weights = create_model()
    print("\n✓ Modelo construido exitosamente")
    print(f"\nPesos de clases: {class_weights}")
