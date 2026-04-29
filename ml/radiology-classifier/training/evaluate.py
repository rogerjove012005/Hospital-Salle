"""
Módulo de evaluación: Matriz de confusión, métricas y análisis detallado
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    confusion_matrix, classification_report, roc_curve, auc,
    precision_recall_curve, f1_score, accuracy_score
)
from sklearn.preprocessing import label_binarize
import json
from pathlib import Path


class ModelEvaluator:
    """Evaluación del modelo"""
    
    def __init__(self, model, class_names):
        self.model = model
        self.class_names = class_names
        self.predictions = None
        self.predictions_proba = None
        self.y_true = None
        self.metrics = {}
    
    def evaluate(self, X_test, y_test):
        """Evalúa el modelo en el conjunto de test"""
        
        # Hacer predicciones
        self.predictions_proba = self.model.predict(X_test, verbose=0)
        self.predictions = np.argmax(self.predictions_proba, axis=1)
        self.y_true = y_test
        
        print("\n" + "="*60)
        print("EVALUACIÓN DEL MODELO")
        print("="*60)
        
        # Calcular métricas
        self._calculate_metrics()
        
        return self.metrics
    
    def _calculate_metrics(self):
        """Calcula todas las métricas"""
        
        accuracy = accuracy_score(self.y_true, self.predictions)
        cm = confusion_matrix(self.y_true, self.predictions)
        
        print(f"\n📊 MÉTRICAS GLOBALES:")
        print(f"  Accuracy: {accuracy:.4f}")
        
        # Reporte de clasificación
        report = classification_report(
            self.y_true, self.predictions,
            target_names=self.class_names,
            output_dict=True
        )
        
        print(f"\n📈 REPORTE POR CLASE:")
        for class_name in self.class_names:
            if class_name in report:
                metrics = report[class_name]
                print(f"\n  {class_name}:")
                print(f"    Precision: {metrics['precision']:.4f}")
                print(f"    Recall: {metrics['recall']:.4f}")
                print(f"    F1-Score: {metrics['f1-score']:.4f}")
        
        # Guardar métricas
        self.metrics = {
            'accuracy': float(accuracy),
            'confusion_matrix': cm.tolist(),
            'classification_report': report,
            'class_names': self.class_names
        }
    
    def plot_confusion_matrix(self, output_dir='ml/radiology-classifier/models'):
        """Grafica la matriz de confusión"""
        
        cm = confusion_matrix(self.y_true, self.predictions)
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # Matriz sin normalizar
        sns.heatmap(
            cm, annot=True, fmt='d',
            xticklabels=self.class_names,
            yticklabels=self.class_names,
            cmap='Blues',
            ax=axes[0],
            cbar_kws={'label': 'Count'}
        )
        axes[0].set_title('Matriz de Confusión (Valores Absolutos)')
        axes[0].set_ylabel('Real')
        axes[0].set_xlabel('Predicho')
        
        # Matriz normalizada
        cm_normalized = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        sns.heatmap(
            cm_normalized, annot=True, fmt='.2%',
            xticklabels=self.class_names,
            yticklabels=self.class_names,
            cmap='RdYlGn',
            ax=axes[1],
            vmin=0, vmax=1,
            cbar_kws={'label': 'Proportion'}
        )
        axes[1].set_title('Matriz de Confusión (Normalizada)')
        axes[1].set_ylabel('Real')
        axes[1].set_xlabel('Predicho')
        
        plt.tight_layout()
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        plt.savefig(f'{output_dir}/confusion_matrix.png', dpi=100, bbox_inches='tight')
        print(f"✓ Matriz de confusión guardada")
        plt.close()
    
    def analyze_errors(self):
        """Analiza los errores cometidos por el modelo"""
        
        print("\n" + "-"*60)
        print("ANÁLISIS DETALLADO DE ERRORES")
        print("-"*60)
        
        cm = confusion_matrix(self.y_true, self.predictions)
        
        print(f"\n🔍 ERRORES CRÍTICOS (Falsos Negativos):")
        
        # FN COVID-19 (no detecta COVID como COVID)
        fn_covid = cm[0, 1] + cm[0, 2]  # Clase 0 = COVID
        print(f"\n  COVID-19 no detectado como COVID: {fn_covid}")
        if fn_covid > 0:
            print(f"    ⚠️  CRÍTICO: Falsos negativos en COVID-19")
            print(f"    Impacto: Pacientes potencialmente infecciosos no aislados")
        
        # FN Neumonía
        fn_pneumonia = cm[1, 0] + cm[1, 2]  # Clase 1 = Neumonía
        print(f"\n  Neumonía no detectada: {fn_pneumonia}")
        if fn_pneumonia > 0:
            print(f"    ⚠️  IMPORTANTE: Falsos negativos en Neumonía")
            print(f"    Impacto: Retraso en tratamiento")
        
        print(f"\n📊 ANÁLISIS POR CLASE:")
        for i, class_name in enumerate(self.class_names):
            tp = cm[i, i]
            fn = cm[i].sum() - tp
            fp = cm[:, i].sum() - tp
            tn = cm.sum() - tp - fn - fp
            
            sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
            
            print(f"\n  {class_name}:")
            print(f"    TP: {tp} | FN: {fn} | FP: {fp} | TN: {tn}")
            print(f"    Sensibilidad (Recall): {sensitivity:.4f}")
            print(f"    Especificidad: {specificity:.4f}")
    
    def plot_roc_curves(self, output_dir='ml/radiology-classifier/models'):
        """Grafica curvas ROC para cada clase"""
        
        # Binarizar labels
        y_bin = label_binarize(self.y_true, classes=range(len(self.class_names)))
        
        fig, axes = plt.subplots(1, 3, figsize=(15, 4))
        
        for i, class_name in enumerate(self.class_names):
            fpr, tpr, _ = roc_curve(y_bin[:, i], self.predictions_proba[:, i])
            roc_auc = auc(fpr, tpr)
            
            axes[i].plot(fpr, tpr, color='darkorange', lw=2,
                        label=f'ROC (AUC = {roc_auc:.3f})')
            axes[i].plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--', label='Random')
            axes[i].set_xlim([0.0, 1.0])
            axes[i].set_ylim([0.0, 1.05])
            axes[i].set_xlabel('False Positive Rate')
            axes[i].set_ylabel('True Positive Rate')
            axes[i].set_title(f'ROC - {class_name}')
            axes[i].legend(loc="lower right")
            axes[i].grid(True, alpha=0.3)
        
        plt.tight_layout()
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        plt.savefig(f'{output_dir}/roc_curves.png', dpi=100, bbox_inches='tight')
        print(f"✓ Curvas ROC guardadas")
        plt.close()
    
    def save_evaluation_report(self, output_dir='ml/radiology-classifier/models'):
        """Guarda reporte completo de evaluación"""
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        report_path = f'{output_dir}/evaluation_report.json'
        with open(report_path, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        
        print(f"✓ Reporte de evaluación guardado en: {report_path}")


def main():
    """Script principal de evaluación"""
    
    from training.train import main as train_main
    
    # Obtener modelo y datos de test del training
    model, trainer, X_test, y_test, class_names = train_main()
    
    # Evaluar
    evaluator = ModelEvaluator(model, class_names)
    metrics = evaluator.evaluate(X_test, y_test)
    
    # Análisis de errores
    evaluator.analyze_errors()
    
    # Visualizaciones
    evaluator.plot_confusion_matrix()
    evaluator.plot_roc_curves()
    
    # Guardar reporte
    evaluator.save_evaluation_report()
    
    print("\n" + "="*60)
    print("✓ EVALUACIÓN COMPLETADA")
    print("="*60)
    
    return evaluator, metrics


if __name__ == '__main__':
    evaluator, metrics = main()
