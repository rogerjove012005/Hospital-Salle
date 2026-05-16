"""
PySpark (local[*]): agregaciones sobre csv_import_rows → JDBC Postgres + Parquet.
"""

from __future__ import annotations

import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def jdbc_url(host: str, port: str, db: str) -> str:
    return f"jdbc:postgresql://{host}:{port}/{db}"


def jdbc_props(user: str, password: str) -> dict[str, str]:
    return {
        "user": user,
        "password": password,
        "driver": "org.postgresql.Driver",
    }


def main() -> int:
    host = os.environ.get("POSTGRES_HOST", "postgres")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ["POSTGRES_DB"]
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    parquet_root = os.environ.get("SPARK_PARQUET_OUT", "/data/processed/spark/csv_row_counts")
    jar = os.environ.get("POSTGRES_JDBC_JAR", "/opt/spark/jars/postgresql-42.7.4.jar")

    url = jdbc_url(host, port, db)
    props = jdbc_props(user, password)

    spark = (
        SparkSession.builder.appName("hospitalCsvAggregates")
        .master("local[*]")
        .config("spark.jars", jar)
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )

    try:
        # Subconsulta: evita palabra reservada position en algunos drivers
        dbtable = (
            '(SELECT batch_id::text AS batch_id, "position" AS row_pos '
            "FROM csv_import_rows) AS src"
        )

        df = (
            spark.read.format("jdbc")
            .option("url", url)
            .option("dbtable", dbtable)
            .option("user", user)
            .option("password", password)
            .option("driver", props["driver"])
            .load()
        )

        by_batch = df.groupBy("batch_id").agg(F.count("*").alias("row_count"))
        counts = by_batch.withColumn("computed_at", F.current_timestamp())

        counts_part = counts.withColumn("pdate", F.to_date(F.col("computed_at")))
        counts_part.write.mode("overwrite").partitionBy("pdate").parquet(parquet_root)

        # Escritura tablas agregado (UUID vía cast desde texto)
        out_counts = counts.select(
            F.col("batch_id").cast("string").alias("batch_id"),
            F.col("row_count").cast("long"),
            F.col("computed_at"),
        )
        out_counts.write.mode("overwrite").option("truncate", "true").jdbc(
            url, "csv_spark_batch_row_counts", properties=props
        )

        totals = df.select(
            F.count("*").alias("total_rows"),
            F.countDistinct("batch_id").alias("batches_with_rows"),
        ).withColumn("computed_at", F.current_timestamp())

        totals = totals.withColumn("id", F.lit(1))

        summary = totals.select("id", "computed_at", "total_rows", "batches_with_rows")
        summary.write.mode("overwrite").option("truncate", "true").jdbc(
            url, "csv_spark_run_summary", properties=props
        )

        sr = summary.collect()[0]
        print({"status": "ok", "parquet": parquet_root, "total_rows": int(sr.total_rows)})
        return 0
    finally:
        spark.stop()


if __name__ == "__main__":
    sys.exit(main())
