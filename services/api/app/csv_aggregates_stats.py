"""Lectura de agregados producidos por el job PySpark (tablas csv_spark_*)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import text

from .auth import UserOut
from .db import engine


class CsvSparkSummaryOut(BaseModel):
    computed_at: datetime | None = None
    total_rows: int = 0
    batches_with_rows: int = 0


class CsvSparkBatchAggOut(BaseModel):
    batch_id: str
    row_count: int
    computed_at: datetime | None = None


class CsvSparkAggregatesOut(BaseModel):
    summary: CsvSparkSummaryOut
    top_batches: list[CsvSparkBatchAggOut] = Field(default_factory=list)


def get_csv_spark_aggregates(user: UserOut, *, top: int = 15) -> CsvSparkAggregatesOut:
    _ = user
    lim = min(max(1, top), 100)
    with engine().connect() as conn:
        srow = conn.execute(
            text(
                """
                SELECT computed_at, total_rows::bigint AS total_rows,
                       batches_with_rows::int AS batches_with_rows
                FROM csv_spark_run_summary
                WHERE id = 1
                """
            )
        ).mappings().fetchone()
        summary_map: dict[str, Any] = dict(srow) if srow else {}
        brow = conn.execute(
            text(
                """
                SELECT batch_id::text AS batch_id, row_count::bigint AS row_count, computed_at
                FROM csv_spark_batch_row_counts
                ORDER BY row_count DESC, batch_id
                LIMIT :lim
                """
            ),
            {"lim": lim},
        ).mappings().all()

    summary = CsvSparkSummaryOut(
        computed_at=summary_map.get("computed_at"),
        total_rows=int(summary_map.get("total_rows") or 0),
        batches_with_rows=int(summary_map.get("batches_with_rows") or 0),
    )
    tops = [
        CsvSparkBatchAggOut(
            batch_id=str(r["batch_id"]),
            row_count=int(r.get("row_count") or 0),
            computed_at=r.get("computed_at"),
        )
        for r in brow
    ]
    return CsvSparkAggregatesOut(summary=summary, top_batches=tops)
