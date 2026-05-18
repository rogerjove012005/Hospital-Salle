# Etapa opcional: entrena empaquetado dentro de la imagen API (dataset sintético académico).
FROM python:3.11-slim AS radiology-build

WORKDIR /src/radiology

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY ml/radiology-classifier /src/radiology

ENV MPLBACKEND=Agg

# Si data/cxr_local ya está preparado (scripts/prepare_radiology_dataset.py en el host),
# el bootstrap entrena con Chest X-Ray real; si no, usa data/synthetic.
RUN pip install --no-cache-dir \
    numpy pillow scikit-learn joblib matplotlib seaborn pandas scipy \
    && python scripts/bootstrap_model.py

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY services/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/api/app ./app

RUN mkdir -p /app/models/radiology

COPY --from=radiology-build /src/radiology/models/model_final.pkl /app/models/radiology/model_final.pkl
COPY --from=radiology-build /src/radiology/models/class_names.json /app/models/radiology/class_names.json
COPY --from=radiology-build /src/radiology/models/evaluation_report.json /app/models/radiology/evaluation_report.json
COPY --from=radiology-build /src/radiology/models/confusion_matrix.png /app/models/radiology/confusion_matrix.png
COPY --from=radiology-build /src/radiology/models/roc_curves.png /app/models/radiology/roc_curves.png
COPY --from=radiology-build /src/radiology/models/clinical_analysis.json /app/models/radiology/clinical_analysis.json

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
