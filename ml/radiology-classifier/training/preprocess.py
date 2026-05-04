"""
Preprocessing: Normalización, redimensionamiento y Data Augmentation
"""

import numpy as np
import pandas as pd
from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split

class DataPreprocessor:
    """Gestor del preprocesamiento de imágenes"""
    
    def __init__(self, img_size=224, batch_size=32, seed=42):
        self.img_size = img_size
        self.batch_size = batch_size
        self.seed = seed
        
        # Estadísticas de normalización (ImageNet)
        self.mean = np.array([0.485, 0.456, 0.406])
        self.std = np.array([0.229, 0.224, 0.225])
    
    def load_and_prepare_data(self, dataset_path='data/synthetic'):
        """Carga todas las imágenes del dataset"""
        dataset_path = Path(dataset_path)
        
        images = []
        labels = []
        class_names = []
        
        for class_idx, class_dir in enumerate(sorted(dataset_path.iterdir())):
            if class_dir.is_dir():
                class_name = class_dir.name
                class_names.append(class_name)
                
                for img_path in class_dir.glob('*.png'):
                    # Cargar imagen en escala de grises
                    img = Image.open(img_path).convert('L')  # Radiografías son escala gris
                    
                    # Redimensionar
                    img = img.resize((self.img_size, self.img_size))
                    
                    # Convertir a array normalizado
                    img_array = np.array(img) / 255.0
                    
                    # Convertir a 3 canales (para modelos RGB)
                    img_array = np.stack([img_array] * 3, axis=-1)
                    
                    images.append(img_array)
                    labels.append(class_idx)
        
        images = np.array(images, dtype=np.float32)
        labels = np.array(labels, dtype=np.int32)
        
        print(f"\n✓ Dataset cargado: {images.shape}")
        print(f"  Clases: {class_names}")
        
        return images, labels, class_names
    
    def split_data(self, images, labels, test_size=0.2, val_size=0.1):
        """Divide los datos en train, validation y test"""
        
        # Split 1: Test set
        X_temp, X_test, y_temp, y_test = train_test_split(
            images, labels, 
            test_size=test_size, 
            random_state=self.seed,
            stratify=labels
        )
        
        # Split 2: Validation set del training
        val_size_adjusted = val_size / (1 - test_size)
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp,
            test_size=val_size_adjusted,
            random_state=self.seed,
            stratify=y_temp
        )
        
        print(f"\n✓ Dataset dividido:")
        print(f"  Train: {X_train.shape[0]} ({X_train.shape[0]/(len(images))*100:.1f}%)")
        print(f"  Validation: {X_val.shape[0]} ({X_val.shape[0]/(len(images))*100:.1f}%)")
        print(f"  Test: {X_test.shape[0]} ({X_test.shape[0]/(len(images))*100:.1f}%)")
        
        return X_train, X_val, X_test, y_train, y_val, y_test
    
    def _augment_image(self, img):
        """Aplica augmentaciones aleatorias a una imagen (numpy)"""
        rng = np.random.default_rng()

        # Flip horizontal
        if rng.random() > 0.5:
            img = img[:, ::-1, :]

        # Rotación ±20°
        angle = rng.uniform(-20, 20)
        from PIL import Image as PILImage
        pil = PILImage.fromarray((img * 255).astype(np.uint8))
        pil = pil.rotate(angle, resample=PILImage.BILINEAR, fillcolor=0)
        img = np.array(pil) / 255.0

        # Desplazamiento ±20%
        shift_x = int(rng.uniform(-0.2, 0.2) * img.shape[1])
        shift_y = int(rng.uniform(-0.2, 0.2) * img.shape[0])
        img = np.roll(img, shift_y, axis=0)
        img = np.roll(img, shift_x, axis=1)

        # Brillo ±20%
        factor = rng.uniform(0.8, 1.2)
        img = np.clip(img * factor, 0, 1)

        return img.astype(np.float32)

    def _batch_generator(self, X, y, shuffle=False):
        """Generador de batches con augmentation opcional"""
        indices = np.arange(len(X))
        if shuffle:
            rng = np.random.default_rng(self.seed)
            rng.shuffle(indices)

        for start in range(0, len(indices), self.batch_size):
            batch_idx = indices[start:start + self.batch_size]
            X_batch = np.array([self._augment_image(X[i]) for i in batch_idx]) if shuffle \
                      else X[batch_idx]
            yield X_batch, y[batch_idx]

    def create_train_generator(self, X_train, y_train):
        """Generador infinito con augmentation para training"""
        while True:
            yield from self._batch_generator(X_train, y_train, shuffle=True)

    def create_val_generator(self, X_val, y_val):
        """Generador infinito sin augmentation para validación"""
        while True:
            yield from self._batch_generator(X_val, y_val, shuffle=False)

    def visualize_augmentation(self, X_sample, y_sample, num_variations=6):
        """Visualiza el efecto de la data augmentation"""
        fig, axes = plt.subplots(2, 3, figsize=(12, 8))
        fig.suptitle('Efecto de Data Augmentation', fontsize=12, fontweight='bold')

        axes[0, 0].imshow(X_sample[..., 0], cmap='gray')
        axes[0, 0].set_title('Original')
        axes[0, 0].axis('off')

        for i in range(1, 6):
            aug = self._augment_image(X_sample)
            row, col = i // 3, i % 3
            axes[row, col].imshow(aug[..., 0], cmap='gray')
            axes[row, col].set_title(f'Augmentación {i}')
            axes[row, col].axis('off')

        plt.tight_layout()
        plt.savefig('data/augmentation_examples.png', dpi=100, bbox_inches='tight')
        print(f"\n✓ Visualización de augmentation guardada")
        plt.close()
    
    def log_preprocessing_decisions(self, class_names):
        """Documenta decisiones de preprocesamiento"""
        print("\n" + "="*60)
        print("DECISIONES DE PREPROCESAMIENTO")
        print("="*60)
        
        print(f"\n📐 TRANSFORMACIONES:")
        print(f"  • Tamaño de imagen: {self.img_size}x{self.img_size}")
        print(f"  • Normalización: 0-255 → 0-1")
        print(f"  • Canales: Escala gris → 3 canales RGB (stacked)")
        
        print(f"\n🔄 DATA AUGMENTATION (solo training):")
        print(f"  • Rotación: ±20°")
        print(f"  • Desplazamiento: ±20%")
        print(f"  • Zoom: ±20%")
        print(f"  • Flip horizontal: Habilitado")
        print(f"  • Brillo: ±20%")
        
        print(f"\n✓ JUSTIFICACIÓN:")
        print(f"  • Aumenta robustez del modelo a variaciones")
        print(f"  • Simula variabilidad en adquisición de imágenes reales")
        print(f"  • Mejora generalización con datasets pequeños")
        
        print(f"\n⚠️  LIMITACIONES ÉTICAS:")
        print(f"  • Data augmentation NO debe generar imágenes clínicamente")
        print(f"    inválidas que podrían entrenar patrones falsos")
        print(f"  • Flip horizontal OK para radiografías de tórax (simétricas)")
        print(f"  • Rotación > 10° podría ser clínicamente problemática")


def main():
    """Script principal de preprocessing"""
    
    print("Iniciando preprocessing del dataset...")
    
    preprocessor = DataPreprocessor(img_size=224, batch_size=32, seed=42)
    
    # Cargar datos
    images, labels, class_names = preprocessor.load_and_prepare_data('data/synthetic')
    
    # Dividir datos
    X_train, X_val, X_test, y_train, y_val, y_test = preprocessor.split_data(
        images, labels, test_size=0.2, val_size=0.1
    )
    
    # Visualizar augmentation
    preprocessor.visualize_augmentation(X_train[0], y_train[0])
    
    # Documentar decisiones
    preprocessor.log_preprocessing_decisions(class_names)
    
    print("\n✓ Preprocessing completado")
    
    return X_train, X_val, X_test, y_train, y_val, y_test, class_names


if __name__ == '__main__':
    X_train, X_val, X_test, y_train, y_val, y_test, class_names = main()
