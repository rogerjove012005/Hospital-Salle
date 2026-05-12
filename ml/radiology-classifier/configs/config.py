import os
from pathlib import Path


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
    
    # Orden estable: índices 0,1,2 usados por el dataset y sklearn
    CLASSES = ['SANA', 'NEUMONIA', 'COVID-19']
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


_RAD_CLASS_ORDER = ("SANA", "NEUMONIA", "COVID-19")


def _radiology_dataset_ready(root: Path) -> bool:
    """True si bajo root hay una carpeta por cada clase con al menos una imagen."""
    root = Path(root)
    if not root.is_dir():
        return False
    ok_ext = {".png", ".jpg", ".jpeg"}
    for name in _RAD_CLASS_ORDER:
        d = root / name
        if not d.is_dir():
            return False
        found = False
        for p in d.iterdir():
            if p.is_file() and p.suffix.lower() in ok_ext:
                found = True
                break
        if not found:
            return False
    return True


def resolve_radiology_dataset_dir() -> Path:
    """
    Orden de preferencia:
    1. RADIOLOGY_DATA_DIR (ruta absoluta o relativa al paquete ml/radiology-classifier)
    2. data/cxr_local/ si está preparado (p. ej. scripts/sync_chest_xray_from_downloads.py)
    3. data/synthetic/
    """
    base = Path(__file__).resolve().parent.parent
    env = os.environ.get("RADIOLOGY_DATA_DIR", "").strip()
    if env:
        p = Path(env)
        if not p.is_absolute():
            p = base / p
        if _radiology_dataset_ready(p):
            return p
    local = base / "data" / "cxr_local"
    if _radiology_dataset_ready(local):
        return local
    return base / "data" / "synthetic"
