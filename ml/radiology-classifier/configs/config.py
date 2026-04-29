import os

class Config:
    """Configuración base del proyecto"""
    
    # Rutas
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    MODELS_DIR = os.path.join(BASE_DIR, 'models')
    
    # Crear directorios si no existen
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    # Dataset
    DATASET_URL = "https://www.kaggle.com/datasets/prashant268/chest-xray-covid19-pneumonia"
    IMG_SIZE = 224
    BATCH_SIZE = 32
    
    # Clases
    CLASSES = ['COVID-19', 'NEUMANIA', 'NORMAL']
    NUM_CLASSES = 3
    
    # Entrenamiento
    EPOCHS = 50
    LEARNING_RATE = 0.001
    VALIDATION_SPLIT = 0.2
    TEST_SPLIT = 0.1
    
    # Data Augmentation
    AUGMENTATION = {
        'rotation_range': 20,
        'width_shift_range': 0.2,
        'height_shift_range': 0.2,
        'horizontal_flip': True,
        'zoom_range': 0.2,
        'fill_mode': 'nearest'
    }
    
    # Modelo
    MODEL_NAME = 'efficientnet_covid_classifier.h5'
    CHECKPOINT_DIR = os.path.join(MODELS_DIR, 'checkpoints')
    
    # Random seed
    SEED = 42
