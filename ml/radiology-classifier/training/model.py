"""
Modelo de clasificación de radiografías con scikit-learn
Pipeline: StandardScaler → PCA → MLPClassifier
"""

import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.decomposition import PCA
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler


class RadiologyModel:
    """Constructor del modelo de clasificación"""

    def __init__(self, num_classes=3, img_size=224):
        self.num_classes = num_classes
        self.img_size = img_size
        self.pipeline = None

    def build_model(self, n_pca_components=100):
        """
        Pipeline:
        1. StandardScaler  — normaliza features (necesario para PCA)
        2. PCA(100)        — reduce de ~150k a 100 componentes principales
        3. MLPClassifier   — red neuronal 256→128→64→num_classes
        """
        self.pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('pca', PCA(n_components=n_pca_components, random_state=42)),
            ('classifier', MLPClassifier(
                hidden_layer_sizes=(256, 128, 64),
                activation='relu',
                solver='adam',
                alpha=1e-4,
                learning_rate='adaptive',
                max_iter=300,
                random_state=42,
                early_stopping=True,
                validation_fraction=0.1,
                n_iter_no_change=15,
                verbose=False,
            ))
        ])
        self._log_architecture_decisions(n_pca_components)
        return self.pipeline

    def get_class_weights(self):
        """Pesos de clase: COVID-19 tiene mayor peso (crítico no detectar)"""
        return {0: 1.5, 1: 1.0, 2: 1.0}

    def _log_architecture_decisions(self, n_pca_components):
        print("\n" + "="*60)
        print("ARQUITECTURA DEL MODELO")
        print("="*60)

        print(f"\n🏗️ PIPELINE SKLEARN:")
        print(f"  StandardScaler → PCA({n_pca_components}) → MLP(256-128-64)")

        print(f"\n🔧 CONFIGURACIÓN:")
        n_features = self.img_size ** 2 * 3
        print(f"  • Entrada: {self.img_size}×{self.img_size}×3 = {n_features:,} features")
        print(f"  • Tras PCA: {n_pca_components} componentes")
        print(f"  • MLP capas ocultas: 256 → 128 → 64")
        print(f"  • Activación: ReLU | Optimizador: Adam")
        print(f"  • Early stopping: activado (patience=15)")

        print(f"\n📊 REGULARIZACIÓN:")
        print(f"  • L2 (alpha): 1e-4")
        print(f"  • Learning rate: adaptativo")

        print(f"\n✓ JUSTIFICACIÓN:")
        print(f"  • PCA: comprime dimensionalidad preservando máxima varianza")
        print(f"  • StandardScaler: PCA requiere features con misma escala")
        print(f"  • MLP: aproximador universal, captura no linealidades")
        print(f"  • Early stopping: previene overfitting automáticamente")

        print(f"\n⚠️  LIMITACIONES VS DEEP LEARNING:")
        print(f"  • Sin transfer learning (EfficientNet/ResNet)")
        print(f"  • PCA lineal: no captura features espaciales complejas")
        print(f"  • En producción: CNN con transfer learning recomendado")


def create_model(num_classes=3, img_size=224, learning_rate=1e-3):
    """Función helper para crear el modelo"""
    print("Construyendo modelo...")
    builder = RadiologyModel(num_classes, img_size)
    pipeline = builder.build_model()
    class_weights = builder.get_class_weights()
    return pipeline, builder, class_weights


if __name__ == '__main__':
    pipeline, builder, class_weights = create_model()
    print("\n✓ Modelo construido exitosamente")
    print(f"Pesos de clases: {class_weights}")
