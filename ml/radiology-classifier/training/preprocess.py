"""
Preprocessing: Normalización, redimensionamiento y Data Augmentation
"""

import numpy as np
import pandas as pd
from pathlib import Path
from PIL import Image
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
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
    
    def create_data_generators(self):
        """Crea generadores con data augmentation"""
        
        # Data augmentation para training
        train_datagen = ImageDataGenerator(
            rotation_range=20,
            width_shift_range=0.2,
            height_shift_range=0.2,
            horizontal_flip=True,
            zoom_range=0.2,
            fill_mode='nearest',
            brightness_range=[0.8, 1.2],  # Variación de contraste
        )
        
        # Sin augmentation para validation y test
        val_test_datagen = ImageDataGenerator()
        
        return train_datagen, val_test_datagen
    
    def create_train_generator(self, X_train, y_train):
        """Crea generador de batch para training"""
        train_datagen, _ = self.create_data_generators()
        
        train_generator = train_datagen.flow(
            X_train, y_train,
            batch_size=self.batch_size,
            shuffle=True,
            seed=self.seed
        )
        
        return train_generator
    
    def create_val_generator(self, X_val, y_val):
        """Crea generador de batch para validación"""
        _, val_test_datagen = self.create_data_generators()
        
        val_generator = val_test_datagen.flow(
            X_val, y_val,
            batch_size=self.batch_size,
            shuffle=False,
            seed=self.seed
        )
        
        return val_generator
    
    def visualize_augmentation(self, X_sample, y_sample, num_variations=6):
        """Visualiza el efecto de la data augmentation"""
        train_datagen, _ = self.create_data_generators()
        
        # Expandir dimensiones para el generador
        X_sample_expanded = np.expand_dims(X_sample, axis=0)
        
        fig, axes = plt.subplots(2, 3, figsize=(12, 8))
        fig.suptitle('Efecto de Data Augmentation', fontsize=12, fontweight='bold')
        
        # Mostrar imagen original
        axes[0, 0].imshow(X_sample[..., 0], cmap='gray')
        axes[0, 0].set_title('Original')
        axes[0, 0].axis('off')
        
        # Mostrar variaciones aumentadas
        aug_count = 1
        for i in range(1, 6):
            # Generar una variación
            aug_batch = next(train_datagen.flow(X_sample_expanded, batch_size=1))
            
            row = i // 3
            col = i % 3
            
            axes[row, col].imshow(aug_batch[0][..., 0], cmap='gray')
            axes[row, col].set_title(f'Augmentación {aug_count}')
            axes[row, col].axis('off')
            aug_count += 1
        
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
