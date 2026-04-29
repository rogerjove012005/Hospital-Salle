"""
Script para descargar y explorar el dataset de radiografías
Utiliza el dataset público de COVID-19 X-ray Chest Images
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import urllib.request
import zipfile
import shutil

class DatasetManager:
    """Gestor del dataset"""
    
    def __init__(self, data_dir='data'):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # URLs de fuentes públicas (alternativas a Kaggle)
        self.sources = {
            'covid': 'https://github.com/ieee8023/covid-chestxray-dataset/archive/master.zip',
            'pneumonia': 'https://data.mendeley.com/public-files/datasets/rscbjbr9sn/files/f12eaf6d-6023-432f-acebd-f6b6d460ca67/file_uploaded',
        }
    
    def create_synthetic_dataset(self, n_samples_per_class=100):
        """
        Crea un dataset sintético para demostración
        En producción se usaría dataset real
        """
        from PIL import Image
        import random
        
        print("Creando dataset sintético...")
        
        classes = ['COVID-19', 'NEUMANIA', 'NORMAL']
        dataset_dir = self.data_dir / 'synthetic'
        
        for class_name in classes:
            class_dir = dataset_dir / class_name
            class_dir.mkdir(parents=True, exist_ok=True)
            
            for i in range(n_samples_per_class):
                # Crear imagen aleatoria en escala de grises (simula radiografía)
                img_array = np.random.randint(50, 200, (224, 224), dtype=np.uint8)
                
                # Añadir "patrones" sintéticos según la clase
                if class_name == 'COVID-19':
                    # Simular infiltrados bilaterales
                    y, x = np.ogrid[:224, :224]
                    mask = ((x - 100)**2 + (y - 100)**2 <= 50**2) | ((x - 124)**2 + (y - 124)**2 <= 50**2)
                    img_array[mask] = np.minimum(img_array[mask] + 40, 255)
                    
                elif class_name == 'NEUMANIA':
                    # Simular consolidación focal
                    y, x = np.ogrid[:224, :224]
                    mask = (x - 80)**2 + (y - 120)**2 <= 40**2
                    img_array[mask] = np.minimum(img_array[mask] + 30, 255)
                
                # Guardar imagen
                img = Image.fromarray(img_array.astype(np.uint8), mode='L')
                img.save(class_dir / f'{class_name}_{i:04d}.png')
        
        print(f"✓ Dataset sintético creado en: {dataset_dir}")
        return dataset_dir
    
    def explore_dataset(self, dataset_path='data/synthetic'):
        """Análisis exploratorio del dataset"""
        print("\n" + "="*60)
        print("ANÁLISIS EXPLORATORIO DEL DATASET")
        print("="*60)
        
        dataset_path = Path(dataset_path)
        
        # Contar imágenes por clase
        class_counts = {}
        total_images = 0
        
        for class_dir in dataset_path.iterdir():
            if class_dir.is_dir():
                class_name = class_dir.name
                img_count = len(list(class_dir.glob('*.png')))
                class_counts[class_name] = img_count
                total_images += img_count
        
        # Crear DataFrame
        df = pd.DataFrame(list(class_counts.items()), columns=['Clase', 'Cantidad'])
        df['Porcentaje'] = (df['Cantidad'] / total_images * 100).round(2)
        
        print(f"\nTotal de imágenes: {total_images}")
        print(f"\nDistribución por clase:\n{df.to_string(index=False)}")
        
        # Estadísticas
        print(f"\nEstadísticas:")
        print(f"  - Imágenes por clase (min): {df['Cantidad'].min()}")
        print(f"  - Imágenes por clase (max): {df['Cantidad'].max()}")
        print(f"  - Imbalance ratio: {df['Cantidad'].max() / df['Cantidad'].min():.2f}x")
        
        # Generar informe de sesgo
        self._generate_bias_report(df)
        
        return df
    
    def _generate_bias_report(self, df):
        """Reporte sobre posibles sesgos en el dataset"""
        print("\n" + "-"*60)
        print("ANÁLISIS DE SESGO Y LIMITACIONES DEL DATASET")
        print("-"*60)
        
        max_class = df['Cantidad'].max()
        min_class = df['Cantidad'].min()
        imbalance = (max_class - min_class) / min_class * 100
        
        print(f"\n📊 SESGO DE CLASE:")
        print(f"  Desbalance: {imbalance:.1f}%")
        
        if imbalance > 20:
            print("  ⚠️  CRÍTICO: Hay desbalance significativo entre clases")
            print("     → Usar técnicas de balanceo (weighted loss, oversampling, etc.)")
        
        print(f"\n📈 CONSIDERACIONES ÉTICAS:")
        print(f"  • Dataset sintético: Validez clínica limitada")
        print(f"  • En producción: Usar dataset real con contexto médico")
        print(f"  • Sesgo de género/edad: Verificar en datos reales")
        print(f"  • Sesgo de equipamiento: Diferentes máquinas de rayos X")
        
        return True
    
    def visualize_samples(self, dataset_path='data/synthetic', samples_per_class=3):
        """Visualiza muestras del dataset"""
        dataset_path = Path(dataset_path)
        
        fig, axes = plt.subplots(3, samples_per_class, figsize=(12, 8))
        fig.suptitle('Muestras del Dataset de Radiografías', fontsize=14, fontweight='bold')
        
        for row, class_dir in enumerate(sorted(dataset_path.iterdir())):
            if class_dir.is_dir():
                images = list(class_dir.glob('*.png'))[:samples_per_class]
                
                for col, img_path in enumerate(images):
                    img = np.array(Image.open(img_path))
                    axes[row, col].imshow(img, cmap='gray')
                    axes[row, col].set_title(class_dir.name, fontsize=10)
                    axes[row, col].axis('off')
        
        plt.tight_layout()
        plt.savefig('data/dataset_samples.png', dpi=100, bbox_inches='tight')
        print(f"\n✓ Visualización guardada en: data/dataset_samples.png")
        plt.close()


def main():
    """Script principal para gestión del dataset"""
    
    manager = DatasetManager('data')
    
    # Crear dataset sintético (en producción: descargar dataset real)
    dataset_path = manager.create_synthetic_dataset(n_samples_per_class=100)
    
    # Exploración
    df = manager.explore_dataset(dataset_path)
    
    # Visualizar muestras
    manager.visualize_samples(dataset_path)
    
    print("\n✓ Setup de dataset completado")


if __name__ == '__main__':
    main()
