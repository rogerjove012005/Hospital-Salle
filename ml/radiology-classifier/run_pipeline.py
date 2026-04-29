"""
Script de prueba end-to-end del modelo completo
Ejecuta: dataset → preprocessing → entrenamiento → evaluación → análisis
"""

import sys
from pathlib import Path
import subprocess

# Agregar ruta del proyecto
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class PipelineTest:
    """Prueba completa del pipeline de IA"""
    
    def __init__(self):
        self.results = {}
    
    def run_full_pipeline(self):
        """Ejecuta todo el pipeline"""
        
        print("\n" + "="*70)
        print("MODELO DE CLASIFICACIÓN DE RADIOGRAFÍAS")
        print("="*70)
        
        # 1. Dataset
        print("\n[1/5] Descargando y preparando dataset...")
        try:
            from data.dataset_manager import DatasetManager
            manager = DatasetManager('data')
            dataset_path = manager.create_synthetic_dataset(n_samples_per_class=100)
            df = manager.explore_dataset(dataset_path)
            manager.visualize_samples(dataset_path)
            self.results['dataset'] = 'OK'
            print("✓ Dataset preparado")
        except Exception as e:
            self.results['dataset'] = f'ERROR: {str(e)}'
            print(f"✗ Error en dataset: {e}")
        
        # 2. Preprocessing
        print("\n[2/5] Preprocesando datos...")
        try:
            from training.preprocess import DataPreprocessor
            preprocessor = DataPreprocessor(img_size=224, batch_size=32)
            images, labels, class_names = preprocessor.load_and_prepare_data('data/synthetic')
            X_train, X_val, X_test, y_train, y_val, y_test = preprocessor.split_data(
                images, labels, test_size=0.2, val_size=0.1
            )
            preprocessor.visualize_augmentation(X_train[0], y_train[0])
            preprocessor.log_preprocessing_decisions(class_names)
            self.results['preprocessing'] = 'OK'
            print("✓ Datos preprocesados")
        except Exception as e:
            self.results['preprocessing'] = f'ERROR: {str(e)}'
            print(f"✗ Error en preprocessing: {e}")
            return
        
        # 3. Modelo y Entrenamiento
        print("\n[3/5] Creando y entrenando modelo...")
        try:
            from training.model import create_model
            from training.train import ModelTrainer
            
            model, builder, class_weights = create_model(
                num_classes=len(class_names),
                img_size=224,
                learning_rate=1e-3
            )
            
            trainer = ModelTrainer(model, class_weights, class_names)
            history = trainer.train(
                X_train, y_train, X_val, y_val,
                epochs=3,
                batch_size=32
            )
            
            trainer.plot_training_history()
            trainer.save_model()
            
            self.results['training'] = 'OK'
            print("✓ Modelo entrenado")
        except Exception as e:
            self.results['training'] = f'ERROR: {str(e)}'
            print(f"✗ Error en entrenamiento: {e}")
            return
        
        # 4. Evaluación
        print("\n[4/5] Evaluando modelo...")
        try:
            from training.evaluate import ModelEvaluator
            
            evaluator = ModelEvaluator(model, class_names)
            metrics = evaluator.evaluate(X_test, y_test)
            evaluator.analyze_errors()
            evaluator.plot_confusion_matrix()
            evaluator.plot_roc_curves()
            evaluator.save_evaluation_report()
            
            self.results['evaluation'] = 'OK'
            print("✓ Evaluación completada")
        except Exception as e:
            self.results['evaluation'] = f'ERROR: {str(e)}'
            print(f"✗ Error en evaluación: {e}")
        
        # 5. Análisis Clínico
        print("\n[5/5] Análisis clínico...")
        try:
            from inference.clinical_analysis import ClinicalAnalysis
            
            analyzer = ClinicalAnalysis(class_names, metrics)
            report = analyzer.generate_clinical_report()
            analyzer.print_summary()
            
            self.results['clinical_analysis'] = 'OK'
            print("✓ Análisis clínico completado")
        except Exception as e:
            self.results['clinical_analysis'] = f'ERROR: {str(e)}'
            print(f"✗ Error en análisis clínico: {e}")
        
        # Resumen final
        self._print_summary()
    
    def _print_summary(self):
        """Imprime resumen de resultados"""
        
        print("\n" + "="*70)
        print("RESUMEN DEL PIPELINE")
        print("="*70)
        
        for step, result in self.results.items():
            status = "✓" if result == 'OK' else "✗"
            print(f"  {status} {step.upper()}: {result}")
        
        print("\n" + "="*70)
        print("ARCHIVOS GENERADOS")
        print("="*70)
        
        paths = [
            'data/synthetic/',
            'data/dataset_samples.png',
            'data/augmentation_examples.png',
            'ml/radiology-classifier/models/best_model.h5',
            'ml/radiology-classifier/models/model_final.h5',
            'ml/radiology-classifier/models/training_history.png',
            'ml/radiology-classifier/models/confusion_matrix.png',
            'ml/radiology-classifier/models/roc_curves.png',
            'ml/radiology-classifier/models/training_info.json',
            'ml/radiology-classifier/models/evaluation_report.json',
            'ml/radiology-classifier/models/clinical_analysis.json'
        ]
        
        for path in paths:
            full_path = Path(path)
            if full_path.exists():
                print(f"  ✓ {path}")
            else:
                print(f"  ○ {path} (será creado durante ejecución)")


def main():
    """Main"""
    
    test = PipelineTest()
    test.run_full_pipeline()


if __name__ == '__main__':
    main()
