# Ética e IA — Módulo de radiología

Complemento específico del clasificador de tórax. Visión global del sistema: [`sistema-hospital-ethica.md`](sistema-hospital-ethica.md).

## Finalidad y límites

- **Soporte al triaje**, no diagnóstico ni tratamiento automatizado.
- Proyecto académico con datos **sintéticos o públicos**; sin validación clínica ni marcado CE/FDA.
- Toda predicción es **probabilística**; el médico conserva la decisión final.

## Riesgos por tipo de error

| Error | Ejemplo | Impacto clínico potencial |
|-------|---------|---------------------------|
| Falso negativo COVID-19 | Clasificar COVID como Normal | Retraso en aislamiento, contagio |
| Falso positivo COVID-19 | Normal clasificado como COVID | Sobrediagnóstico, ansiedad, recursos |
| Confusión Neumonía ↔ COVID-19 | Patrones radiológicos similares | Tratamiento o protocolo inadecuado |

La matriz de confusión y `clinical_analysis.json` documentan estos casos para la defensa.

## Sesgos

- Dataset sintético o pequeño: no representa edad, sexo, etnia ni equipos de distintos fabricantes.
- Posible desbalance entre clases en entrenamiento.
- **Mitigación docente:** transparencia en métricas, no despliegue real sin auditoría externa.

## Privacidad (RGPD / LOPD marco docente)

- No subir radiografías reales de pacientes al entorno de demostración.
- Si se usan datasets públicos, respetar licencias (p. ej. CC, uso investigación).
- Logs de API no deben almacenar imágenes en texto plano más allá del procesamiento en memoria.

## Decisiones automatizadas (Art. 22 RGPD — contexto real)

En producción haría falta: base legal, información al interesado, derecho a intervención humana y revisión periódica del modelo. En esta práctica se **simula** el flujo con supervisión médico explícita en la UI.

## Recomendaciones si el hospital lo desplegara

1. Dataset multicéntrico y validación con radiólogos.
2. Explicabilidad (Grad-CAM, informe de atención).
3. Umbral de confianza y derivación manual si score < τ.
4. Registro de versiones de modelo y trazabilidad de cada inferencia.
5. Comité de ética clínica y DPIA.
