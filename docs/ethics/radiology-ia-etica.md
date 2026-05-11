# Ética y cumplimiento normativo — módulo de radiografía (IA)

## 1. Finalidad y límites del sistema

El clasificador de radiografías de tórax se entrega como **herramienta de apoyo al triaje y a la docencia**. **No** es un producto sanitario certificado (no CE MDR / no FDA 510(k) en esta iteración). La decisión de aislamiento, tratamiento o alta **solo** puede tomarla personal clínico competente.

## 2. Sesgos en datos y en el modelo

| Riesgo | Mitigación en proyecto | Mejora en entorno real |
|--------|------------------------|-------------------------|
| **Datos sintéticos** no representan variabilidad de equipos, centros ni poblaciones. | Documentar origen; no extrapolar tasas de error a producción. | Entrenar y validar con cohortes multicéntricas y metadatos (sensor, kVp, población). |
| **Desbalance** de clases o prevalencia artificial. | Pesos de muestra y splits estratificados. | Ajuste de umbral por clase según coste asimétrico (FN COVID). |
| **Sesgo demográfico** (sexo, edad, etnia) no modelado. | Incluir en memoria técnica como deuda. | Auditorías de equidad y subgrupos. |

## 3. Falsos negativos y falsos positivos (impacto clínico)

- **Falso negativo en COVID-19** o neumonía: retraso en aislamiento o antibioterapia; daño colectivo en enfermedades transmisibles.
- **Falso positivo**: sobrecarga de confirmación imagenológica y ansiedad; suele ser preferible a FN en triaje infeccioso si los recursos lo permiten.

El análisis cuantitativo vive en la **matriz de confusión**; el análisis cualitativo en `clinical_analysis.json` y en la SDD `docs/specs/radiology-classifier.md`.

## 4. Privacidad y protección de datos

- Las imágenes por defecto son **generadas sintéticamente** y no corresponden a pacientes.
- Si en el futuro se conectan **DICOM reales**, aplican **RGPD** (bases jurídicas, minimización, DPIA), **Ley 41/2002** (España, historial clínico) y políticas internas del hospital.
- Los **uploads** a `/radiology/predict` deben gobernarse con **retención mínima**, logs sin datos sensibles innecesarios y cifrado en tránsito (TLS en producción).

## 5. Transparencia y explicabilidad

- El baseline actual es una **caja opaca** a nivel clínico (MLP sobre PCA). Se recomienda roadmap hacia **explicabilidad** (Grad-CAM, LIME sobre superpixeles) antes de uso asistencial real.

## 6. Responsabilidad y gobernanza

- Versión de modelo y trazabilidad de predicción (quién, cuándo, versión de artefacto).
- **Human-in-the-loop** obligatorio.
- Plan de retirada si el rendimiento en datos reales cae por deriva de dominio.
