"""Append-only Delta Lake persistence for computed PAL events.

Additive stand-in for ``med.storage.sqlite_store.PalStore``: same 16 contract
columns, plus ``created_at`` stamped by the database at save time. The v0
SQLite store is untouched and still used by the v0 demo.
"""

from __future__ import annotations

from delta.tables import DeltaTable
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from med_spark.batch import PAL_COLUMNS


class DeltaPalStore:
    """Append-only Delta table of PAL rows at ``base_path``."""

    def __init__(self, spark, base_path: str = "data/delta"):
        self.spark = spark
        self.base_path = base_path

    def exists(self) -> bool:
        """True when a Delta table (a ``_delta_log``) is present at ``base_path``."""
        return bool(DeltaTable.isDeltaTable(self.spark, self.base_path))

    def save(self, df: DataFrame) -> None:
        """Append ``df`` to the table, stamping ``created_at`` server-side."""
        missing = [c for c in PAL_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                "cannot save: frame is missing PAL column(s): " + ", ".join(missing)
            )
        to_write = df.select(*[F.col(c) for c in PAL_COLUMNS]).withColumn(
            "created_at", F.current_timestamp()
        )
        to_write.write.format("delta").mode("append").save(self.base_path)

    def count(self) -> int:
        """Row count; 0 when no table exists yet."""
        if not self.exists():
            return 0
        return int(self.list_all().count())

    def list_all(self) -> DataFrame:
        """All rows, ordered by write time."""
        if not self.exists():
            raise FileNotFoundError(f"no Delta table at {self.base_path!r}")
        return self.spark.read.format("delta").load(self.base_path).orderBy("created_at")
