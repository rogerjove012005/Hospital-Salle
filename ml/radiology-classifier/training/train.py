"""
Script de entrenamiento del modelo de clasificación de radiografías
"""

import numpy as np
import os
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import json
import joblib
from sklearn.utils.class_weight import compute_sample_weight

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
        """Entrena el pipeline sklearn"""

        print("\n" + "="*60)
        print("INICIANDO ENTRENAMIENTO")
        print("="*60)
        print(f"  Train: {len(X_train)} muestras")
        print(f"  Validación: {len(X_val)} muestras")

        # Aplanar imágenes: (N, H, W, C) → (N, H*W*C)
        X_train_flat = X_train.reshape(len(X_train), -1)
        X_val_flat = X_val.reshape(len(X_val), -1)

        # Sample weights para manejar desbalance de clases
        sample_weights = compute_sample_weight(
            class_weight=self.class_weights, y=y_train
        )

        print("\nEntrenando...")
        self.model.fit(
            X_train_flat, y_train,
            classifier__sample_weight=sample_weights
        )

        val_score = self.model.score(X_val_flat, y_val)

        clf = self.model.named_steps['classifier']
        self.history = {
            'loss': clf.loss_curve_,
            'val_accuracy': getattr(clf, 'validation_scores_', []),
            'n_iter': clf.n_iter_,
        }

        print(f"\n✓ Entrenamiento completado")
        print(f"  Iteraciones: {clf.n_iter_}")
        print(f"  Accuracy validación: {val_score:.4f}")

        return self.history

    def plot_training_history(self, output_dir='ml/radiology-classifier/models'):
        """Grafica la historia de entrenamiento"""
        os.makedirs(output_dir, exist_ok=True)

        fig, axes = plt.subplots(1, 2, figsize=(12, 4))

        axes[0].plot(self.history['loss'], color='royalblue', label='Train Loss')
        axes[0].set_title('Curva de Loss')
        axes[0].set_ylabel('Loss')
        axes[0].set_xlabel('Iteración')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        if self.history['val_accuracy']:
            axes[1].plot(self.history['val_accuracy'], color='darkorange', label='Val Accuracy')
            axes[1].set_title('Accuracy de Validación (Early Stopping)')
            axes[1].set_ylabel('Accuracy')
            axes[1].set_xlabel('Iteración')
            axes[1].legend()
            axes[1].grid(True, alpha=0.3)
        else:
            axes[1].text(0.5, 0.5, 'No disponible', ha='center', va='center',
                         transform=axes[1].transAxes)
            axes[1].set_title('Validación')

        plt.tight_layout()
        plt.savefig(f'{output_dir}/training_history.png', dpi=100, bbox_inches='tight')
        print(f"✓ Gráficas guardadas en: {output_dir}/training_history.png")
        plt.close()

    def save_model(self, output_dir='ml/radiology-classifier/models'):
        """Guarda el modelo entrenado con joblib"""
        os.makedirs(output_dir, exist_ok=True)

        model_path = f'{output_dir}/model_final.pkl'
        joblib.dump(self.model, model_path)
        print(f"✓ Modelo guardado en: {model_path}")

        clf = self.model.named_steps['classifier']
        train_info = {
            'classes': self.class_names,
            'iterations_trained': self.history['n_iter'],
            'final_val_accuracy': float(getattr(clf, 'best_validation_score_', 0.0)),
            'final_loss': float(self.history['loss'][-1]) if self.history['loss'] else None,
            'class_weights': self.class_weights,
        }

        info_path = f'{output_dir}/training_info.json'
        with open(info_path, 'w') as f:
            json.dump(train_info, f, indent=2)

        print(f"✓ Info de entrenamiento guardada en: {info_path}")


def main():
    """Script principal de entrenamiento"""
    print("Iniciando pipeline de entrenamiento...")

    preprocessor = DataPreprocessor(img_size=224, batch_size=32, seed=42)
    images, labels, class_names = preprocessor.load_and_prepare_data('data/synthetic')
    X_train, X_val, X_test, y_train, y_val, y_test = preprocessor.split_data(
        images, labels, test_size=0.2, val_size=0.1
    )

    model, builder, class_weights = create_model(
        num_classes=len(class_names), img_size=224, learning_rate=1e-3
    )

    trainer = ModelTrainer(model, class_weights, class_names)
    history = trainer.train(X_train, y_train, X_val, y_val, epochs=50, batch_size=32)
    trainer.plot_training_history()
    trainer.save_model()

    print("\n" + "="*60)
    print("✓ ENTRENAMIENTO COMPLETADO")
    print("="*60)

    return model, trainer, X_test, y_test, class_names


if __name__ == '__main__':
    model, trainer, X_test, y_test, class_names = main()
