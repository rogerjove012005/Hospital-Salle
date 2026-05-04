"""
Script de entrenamiento del modelo de clasificación de radiografías
"""

import numpy as np
import os
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import json

# Agregar ruta del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

from training.preprocess import DataPreprocessor
from training.model import create_model


class ModelTrainer:
    """Entrena el modelo"""
    
    def __init__(self, model, class_weights, class_names):
        self.model = model
        self.class_weights = class_weights
        self.class_names = class_names
        self.history = None
    
    def train(self, X_train, y_train, X_val, y_val, epochs=50, batch_size=32):
        """Entrena el modelo"""
        
        # Convertir labels a one-hot
        y_train_onehot = self._to_onehot(y_train)
        y_val_onehot = self._to_onehot(y_val)
        
        print("\n" + "="*60)
        print("INICIANDO ENTRENAMIENTO")
        print("="*60)

        # Obtener callbacks
        from training.model import RadiologyModel
        builder = RadiologyModel(num_classes=len(self.class_names))
        callbacks = builder.get_callbacks()

        # Entrenar pasando arrays numpy directamente (necesario para usar class_weight)
        self.history = self.model.fit(
            X_train, y_train_onehot,
            batch_size=batch_size,
            validation_data=(X_val, y_val_onehot),
            epochs=epochs,
            callbacks=callbacks,
            class_weight=self.class_weights,
            shuffle=True,
            verbose=1
        )
        
        print("\n✓ Entrenamiento completado")
        return self.history
    
    def _to_onehot(self, labels):
        """Convierte labels a one-hot encoding"""
        num_classes = len(self.class_names)
        onehot = np.zeros((len(labels), num_classes))
        onehot[np.arange(len(labels)), labels] = 1
        return onehot
    
    def plot_training_history(self, output_dir='ml/radiology-classifier/models'):
        """Grafica la historia de entrenamiento"""
        
        os.makedirs(output_dir, exist_ok=True)
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # Accuracy
        axes[0, 0].plot(self.history.history['accuracy'], label='Train')
        axes[0, 0].plot(self.history.history['val_accuracy'], label='Validation')
        axes[0, 0].set_title('Accuracy')
        axes[0, 0].set_ylabel('Accuracy')
        axes[0, 0].set_xlabel('Epoch')
        axes[0, 0].legend()
        axes[0, 0].grid(True)
        
        # Loss
        axes[0, 1].plot(self.history.history['loss'], label='Train')
        axes[0, 1].plot(self.history.history['val_loss'], label='Validation')
        axes[0, 1].set_title('Loss')
        axes[0, 1].set_ylabel('Loss')
        axes[0, 1].set_xlabel('Epoch')
        axes[0, 1].legend()
        axes[0, 1].grid(True)
        
        # Precision
        if 'precision' in self.history.history:
            axes[1, 0].plot(self.history.history['precision'], label='Train')
            axes[1, 0].plot(self.history.history['val_precision'], label='Validation')
            axes[1, 0].set_title('Precision')
            axes[1, 0].set_ylabel('Precision')
            axes[1, 0].set_xlabel('Epoch')
            axes[1, 0].legend()
            axes[1, 0].grid(True)
        
        # Recall
        if 'recall' in self.history.history:
            axes[1, 1].plot(self.history.history['recall'], label='Train')
            axes[1, 1].plot(self.history.history['val_recall'], label='Validation')
            axes[1, 1].set_title('Recall')
            axes[1, 1].set_ylabel('Recall')
            axes[1, 1].set_xlabel('Epoch')
            axes[1, 1].legend()
            axes[1, 1].grid(True)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/training_history.png', dpi=100, bbox_inches='tight')
        print(f"✓ Gráficas guardadas en: {output_dir}/training_history.png")
        plt.close()
    
    def save_model(self, output_dir='ml/radiology-classifier/models'):
        """Guarda el modelo entrenado"""
        os.makedirs(output_dir, exist_ok=True)
        
        model_path = f'{output_dir}/model_final.h5'
        self.model.save(model_path)
        print(f"✓ Modelo guardado en: {model_path}")
        
        # Guardar información de entrenamiento
        train_info = {
            'classes': self.class_names,
            'epochs_trained': len(self.history.history['loss']),
            'final_accuracy': float(self.history.history['val_accuracy'][-1]),
            'final_loss': float(self.history.history['val_loss'][-1]),
            'class_weights': self.class_weights
        }
        
        info_path = f'{output_dir}/training_info.json'
        with open(info_path, 'w') as f:
            json.dump(train_info, f, indent=2)
        
        print(f"✓ Info de entrenamiento guardada en: {info_path}")


def main():
    """Script principal de entrenamiento"""
    
    print("Iniciando pipeline de entrenamiento...")
    
    # 1. Preparar datos
    print("\n1. Preparando datos...")
    preprocessor = DataPreprocessor(img_size=224, batch_size=32, seed=42)
    images, labels, class_names = preprocessor.load_and_prepare_data('data/synthetic')
    X_train, X_val, X_test, y_train, y_val, y_test = preprocessor.split_data(
        images, labels, test_size=0.2, val_size=0.1
    )
    
    # 2. Crear modelo
    print("\n2. Creando modelo...")
    model, builder, class_weights = create_model(
        num_classes=len(class_names),
        img_size=224,
        learning_rate=1e-3
    )
    
    # 3. Entrenar
    print("\n3. Entrenando modelo...")
    trainer = ModelTrainer(model, class_weights, class_names)
    history = trainer.train(
        X_train, y_train, X_val, y_val,
        epochs=3,  # Pocos epochs para demo rápido
        batch_size=32
    )
    
    # 4. Guardar resultados
    print("\n4. Guardando resultados...")
    trainer.plot_training_history()
    trainer.save_model()
    
    print("\n" + "="*60)
    print("✓ ENTRENAMIENTO COMPLETADO")
    print("="*60)
    
    return model, trainer, X_test, y_test, class_names


if __name__ == '__main__':
    model, trainer, X_test, y_test, class_names = main()
