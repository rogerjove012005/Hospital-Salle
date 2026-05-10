FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY automated_csv_ingest.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "automated_csv_ingest.py"]
