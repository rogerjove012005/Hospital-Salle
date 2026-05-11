FROM apache/spark-py:3.5.3

USER root

RUN apt-get update \
  && apt-get install -y --no-install-recommends curl \
  && curl -fsSL -o /opt/spark/jars/postgresql-42.7.4.jar \
    https://jdbc.postgresql.org/download/postgresql-42.7.4.jar \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY spark_aggregate.py run_loop.sh ./
RUN chmod +x run_loop.sh

ENV POSTGRES_JDBC_JAR=/opt/spark/jars/postgresql-42.7.4.jar \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["/app/run_loop.sh"]
