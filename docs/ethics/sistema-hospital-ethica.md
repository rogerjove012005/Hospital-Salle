# Ética del sistema hospitalario (visión global)

Documento complementario a [`radiology-ia-etica.md`](radiology-ia-etica.md). Aplica a todo el portal laSalle Health Center.

## Principios

1. **Finalidad académica:** demostración de ingesta, analítica y apoyo a la decisión; no sustituye el juicio clínico.
2. **Minimización de datos:** cada rol ve solo lo necesario (paciente → expediente propio; médico → cartera; admin → operaciones).
3. **Transparencia:** métricas de IA RX publicadas con matriz de confusión y limitaciones conocidas.
4. **Trazabilidad:** eventos de pipeline y calidad persistidos para auditoría docente.

## Decisiones automatizadas

| Proceso | Automatización | Supervisión humana |
|---------|----------------|-------------------|
| Ingesta CSV | Worker + reglas de calidad | Admin revisa alertas |
| Agregación Spark | Job periódico | Informe operativo |
| Radiología IA | Inferencia probabilística | Médico valida imagen y contexto |

## RGPD (marco docente)

- Datos sintéticos o anonimizados en los CSV de ejemplo.
- No usar credenciales reales de pacientes en entornos compartidos.
- Informes HTML del centro de control sin exportación masiva de PII.

## Sesgo y equidad

- El clasificador RX se entrena con dataset académico limitado; no garantizar paridad entre subpoblaciones.
- Los KPIs operativos no deben usarse para evaluación individual de profesionales.

## Contacto y gobernanza

Incidencias éticas del proyecto: canal docente del máster / responsable de la práctica. Cambios en reglas de acceso deben registrarse en el diario de desarrollo IA.
