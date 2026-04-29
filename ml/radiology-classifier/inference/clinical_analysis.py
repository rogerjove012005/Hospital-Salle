"""
Análisis Clínico: Reflexión crítica sobre el modelo desde perspectiva médica
Documento: Justificación técnica y consideraciones éticas/legales
"""

import json
from pathlib import Path
from datetime import datetime


class ClinicalAnalysis:
    """Análisis clínico y consideraciones del modelo"""
    
    def __init__(self, class_names, metrics=None):
        self.class_names = class_names
        self.metrics = metrics or {}
        self.analysis_report = {}
    
    def generate_clinical_report(self, output_dir='ml/radiology-classifier/models'):
        """Genera reporte clínico completo"""
        
        print("\n" + "="*60)
        print("ANÁLISIS CLÍNICO DEL MODELO")
        print("="*60)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'clinical_reasoning': self._clinical_reasoning(),
            'error_analysis': self._error_analysis(),
            'ethical_considerations': self._ethical_considerations(),
            'limitations': self._limitations(),
            'recommendations': self._recommendations()
        }
        
        self.analysis_report = report
        
        # Guardar reporte
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        report_path = f'{output_dir}/clinical_analysis.json'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Reporte clínico guardado en: {report_path}")
        
        return report
    
    def _clinical_reasoning(self):
        """Razonamiento clínico detrás del modelo"""
        
        print("\n📋 RAZONAMIENTO CLÍNICO:")
        
        reasoning = {
            'problem_statement': (
                'Clasificación automática de radiografías de tórax para detectar '
                'COVID-19, Neumonía y casos normales. En entorno hospitalario, '
                'un sistema automatizado puede:',
                [
                    'Acelerar triaje inicial de pacientes',
                    'Reducir carga de radiologistas',
                    'Servir como herramienta de soporte (NO reemplazo)',
                    'Detectar casos con mayor rapidez'
                ]
            ),
            'model_choice': {
                'why_cnn': 'Las radiografías son datos visuales; CNN capta patrones espaciales',
                'why_transfer_learning': (
                    'ImageNet proporciona features generales de imágenes. '
                    'Fine-tuning las adapta a radiografías médicas'
                ),
                'why_efficientnet': (
                    'Balance óptimo entre precisión y eficiencia. '
                    'Importante para deployment hospitalario'
                )
            },
            'clinical_implications': {
                'sensitivity_vs_specificity': (
                    'En radiografías: buscamos ALTA SENSIBILIDAD (pocos falsos negativos) '
                    'para COVID-19 (contagioso, crítico). '
                    'ESPECIFICIDAD importante pero secundaria'
                ),
                'false_negatives_critical': (
                    'Un FN en COVID-19 = paciente no diagnosticado podría contagiar a otros. '
                    'INACEPTABLE en protocolo real'
                ),
                'false_positives_acceptable': (
                    'Un FP genera cautela → confirmación por radiólogo. '
                    'Mejor que FN'
                )
            }
        }
        
        print(f"  ✓ Modelo diseñado para soporte clínico (no reemplazo)")
        print(f"  ✓ Prioriza sensibilidad en patologías críticas")
        
        return reasoning
    
    def _error_analysis(self):
        """Análisis de errores clínicamente relevante"""
        
        print("\n🔍 ANÁLISIS DE ERRORES:")
        
        analysis = {
            'critical_error_types': {
                'FN_COVID': {
                    'definition': 'Detecta COVID como Normal o Neumonía',
                    'clinical_impact': 'CRÍTICO - Paciente no aislado, riesgo de contagio',
                    'hospital_action': 'Revisión manual antes de dar alta',
                    'prevention': 'Aumentar sensibilidad (bajar threshold de COVID)',
                    'severity': 'CRÍTICA'
                },
                'FN_PNEUMONIA': {
                    'definition': 'Detecta Neumonía como Normal',
                    'clinical_impact': 'IMPORTANTE - Retraso en tratamiento antibiótico',
                    'hospital_action': 'Revisión por síntomas clínicos',
                    'severity': 'ALTA'
                },
                'FP_COVID': {
                    'definition': 'Detecta Normal/Neumonía como COVID',
                    'clinical_impact': 'TOLERABLE - Revisión por radiólogo confirma diagnóstico',
                    'hospital_action': 'Aislamiento preventivo → confirmación',
                    'severity': 'MEDIA'
                }
            },
            'confusion_matrix_interpretation': (
                'Ver matriz de confusión para identificar:'
                '1. Qué se confunde con qué'
                '2. Dónde están los falsos negativos'
                '3. Tasas de error por clase'
            )
        }
        
        print(f"  ✓ COVID no detectado: CRÍTICO")
        print(f"  ✓ Neumonía no detectada: IMPORTANTE")
        
        return analysis
    
    def _ethical_considerations(self):
        """Consideraciones éticas y legales"""
        
        print("\n⚖️ CONSIDERACIONES ÉTICAS:")
        
        ethics = {
            'bias_in_data': {
                'potential_biases': [
                    'Sesgo de género: Dataset podría estar sesgado por género',
                    'Sesgo de edad: Distribución desigual de edades',
                    'Sesgo de equipamiento: Diferentes máquinas de rayos X',
                    'Sesgo geográfico: Datos de una región particular',
                    'Sesgo de prevalencia: Proporción de COVID/Neumonía podría no ser realista'
                ],
                'mitigation_strategies': [
                    'Validar modelo en múltiples hospitales',
                    'Testear en diferentes grupos demográficos',
                    'Auditoría regular de sesgo',
                    'Documentar composición del dataset'
                ]
            },
            'safety_and_liability': {
                'disclaimer': (
                    'El modelo es herramienta de APOYO, no diagnóstico definitivo. '
                    'Decisión clínica final SIEMPRE por radiólogo/médico'
                ),
                'regulatory_compliance': [
                    'FDA approval NO obtenido (modelo de investigación)',
                    'Cumplir HIPAA para datos de pacientes reales',
                    'GDPR si hay datos europeos',
                    'Auditoría de algoritmos médicos requerida'
                ],
                'documentation_requirements': [
                    'Logging de todas las predicciones',
                    'Trazabilidad: quién hace clic, cuándo, por qué',
                    'Alertas ante confianza baja',
                    'Registro de correcciones humanas'
                ]
            },
            'equity_and_access': {
                'considerations': [
                    'Modelo accesible a hospitales pequeños también',
                    'No crear gap entre hospitales con/sin IA',
                    'Formación para personal médico en limitaciones del modelo',
                    'Evitar falsa confianza en predicciones'
                ]
            }
        }
        
        print(f"  ✓ Herramienta de APOYO, no diagnóstico definitivo")
        print(f"  ✓ Requiere validación en datos reales")
        print(f"  ✓ Necesario cumplimiento regulatorio")
        
        return ethics
    
    def _limitations(self):
        """Limitaciones del modelo"""
        
        print("\n⚠️ LIMITACIONES:")
        
        limitations = {
            'data_limitations': [
                'Dataset sintético: Validez clínica limitada',
                'Pequeño volumen: Resultados pueden no generalizarse',
                'Sin datos de pacientes reales',
                'Sin seguimiento de outcomes clínicos'
            ],
            'model_limitations': [
                'CNN es "caja negra": No explica razonamiento',
                'Transfer Learning puede introducir artefactos de ImageNet',
                'No captura contexto clínico del paciente',
                'Sensible a calidad de imagen',
                'Performance puede degradarse con nuevos equipos'
            ],
            'deployment_limitations': [
                'Requiere GPU/hardware especializado',
                'Latencia: No aplicable a urgencias en tiempo real',
                'Actualización del modelo: Proceso complejo',
                'Integración con sistemas hospitalarios: Desafío',
                'Cambios epidemiológicos: Variantes de COVID no consideradas'
            ],
            'clinical_limitations': [
                'No diferencia entre COVID-19 severo y leve',
                'No proporciona información de prognóstico',
                'Basado en tórax, ignora síntomas sistémicos',
                'No identifica comorbilidades',
                'No reemplaza evaluación clínica completa'
            ]
        }
        
        print(f"  • Dataset sintético")
        print(f"  • Modelo tipo \"caja negra\"")
        print(f"  • No generaliza perfectamente a datos reales")
        
        return limitations
    
    def _recommendations(self):
        """Recomendaciones para mejora y deployment"""
        
        print("\n💡 RECOMENDACIONES:")
        
        recommendations = {
            'for_improvement': [
                {
                    'title': 'Usar dataset real',
                    'description': 'COVIDx, ChexPert, o Padchest con datos reales',
                    'impact': 'Validez clínica real'
                },
                {
                    'title': 'Explicabilidad (Explainable AI)',
                    'description': 'GradCAM para mostrar qué mira el modelo',
                    'impact': 'Confianza clínica, auditoría regulatoria'
                },
                {
                    'title': 'Validación clínica externa',
                    'description': 'Test en múltiples hospitales y radiologistas',
                    'impact': 'Generalización a mundo real'
                },
                {
                    'title': 'Análisis de calibración',
                    'description': 'Las probabilidades deben ser confiables',
                    'impact': 'Mejor toma de decisiones'
                }
            ],
            'for_deployment': [
                'Sistema de alertas para baja confianza',
                'Logging completo de predicciones',
                'Interfaz clara (evitar gaming del sistema)',
                'Formación de usuarios',
                'Evaluación periódica de performance',
                'Plan de rollback si performance degrada'
            ],
            'for_ethics_compliance': [
                'Auditoría de sesgo pre-deployment',
                'Protocolo de manejo de datos sensibles',
                'Consentimiento informado de pacientes',
                'Política de uso responsable',
                'Oversight board médico-técnico'
            ]
        }
        
        print(f"  1. Validar con datos reales")
        print(f"  2. Implementar explicabilidad")
        print(f"  3. Evaluar con expertos clínicos")
        
        return recommendations
    
    def print_summary(self):
        """Imprime resumen ejecutivo"""
        
        print("\n" + "="*60)
        print("RESUMEN EJECUTIVO - ANÁLISIS CLÍNICO")
        print("="*60)
        
        print(f"""
✅ PUNTOS FUERTES:
  • Arquitectura CNN adecuada para imágenes médicas
  • Transfer Learning acelera aprendizaje
  • Matriz de confusión muestra dónde falla el modelo

⚠️ LIMITACIONES CRÍTICAS:
  • Dataset sintético: NO aplicable clínicamente
  • Falsos negativos en COVID podrían ser críticos
  • No explicable: No sabemos por qué predice algo
  • Requiere validación exhaustiva en datos reales

📋 PRÓXIMOS PASOS:
  1. Obtener dataset real (COVID-19 X-Ray Chest)
  2. Implementar técnicas de explicabilidad (GradCAM)
  3. Validar con radiologistas expertos
  4. Cumplir normativa regulatoria (FDA 510k)
  5. Implementar monitorización en producción

🏥 CONSIDERACIONES HOSPITALARIAS:
  • Nunca debe reemplazar diagnóstico médico
  • Sistema de apoyo únicamente
  • Formación obligatoria del personal
  • Protocolo de escalada ante anomalías
  • Auditoría regular de decisions
        """)


def main():
    """Script principal de análisis clínico"""
    
    class_names = ['COVID-19', 'NEUMANIA', 'NORMAL']
    
    analyzer = ClinicalAnalysis(class_names)
    
    # Generar reporte
    report = analyzer.generate_clinical_report()
    
    # Imprimir resumen
    analyzer.print_summary()
    
    print("\n✓ Análisis clínico completado")
    
    return analyzer


if __name__ == '__main__':
    analyzer = main()
