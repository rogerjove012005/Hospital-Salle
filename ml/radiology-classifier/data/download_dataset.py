"""
Script para descarga del dataset
Descarga dataset público COVID-19 X-ray o crea datos sintéticos para demostración
"""

from data.dataset_manager import DatasetManager

if __name__ == '__main__':
    print("Inicializando descarga y preparación del dataset...\n")
    
    manager = DatasetManager('data')
    
    # Crear dataset sintético para demostración
    # En producción: implementar descarga de dataset real
    dataset_path = manager.create_synthetic_dataset(n_samples_per_class=100)
    
    # Exploración
    df = manager.explore_dataset(dataset_path)
    
    # Visualizar
    manager.visualize_samples(dataset_path)
    
    print("\n" + "="*60)
    print("Dataset preparado y listo para preprocessing")
    print("="*60)
