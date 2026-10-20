"""BigQuery connector (real client library).

Uses ``google-cloud-bigquery`` with Application Default Credentials when it
is installed and ``BIGQUERY_PROJECT`` / ``BIGQUERY_DATASET`` are set. When
they are missing, construction raises a clear ``RuntimeError`` — use
``--source local`` for the offline demo.
"""

from __future__ import annotations

import os

from .base import WarehouseConnector


class BigQueryConnector(WarehouseConnector):
    name = "bigquery"

    def __init__(self):
        missing = [v for v in ("BIGQUERY_PROJECT", "BIGQUERY_DATASET")
                   if not os.environ.get(v)]
        if missing:
            raise RuntimeError(
                "BigQuery settings missing (env vars: " + ", ".join(missing)
                + "). Use --source local for the offline demo.")
        try:
            from google.cloud import bigquery
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "google-cloud-bigquery is not installed; "
                "install requirements-connectors.txt") from exc
        self._client = bigquery.Client(project=os.environ["BIGQUERY_PROJECT"])
        self._project = os.environ["BIGQUERY_PROJECT"]
        self._dataset = os.environ["BIGQUERY_DATASET"]
        self._columns_cache: dict[str, list[str]] = {}

    def list_tables(self) -> list[str]:
        tables = self._client.list_tables(f"{self._project}.{self._dataset}")
        return sorted(t.table_id for t in tables)

    def table_columns(self, table: str) -> list[str]:
        if table not in self._columns_cache:
            ref = self._client.get_table(f"{self._project}.{self._dataset}.{table}")
            self._columns_cache[table] = [f.name for f in ref.schema]
        return self._columns_cache[table]

    def fetch_table(self, table: str) -> list[dict]:
        cols = self.table_columns(table)
        if not cols:
            return []
        col_sql = ", ".join(f"`{c}`" for c in cols)
        query = f"SELECT {col_sql} FROM `{self._project}.{self._dataset}.{table}`"
        result = self._client.query(query).result()
        return [{c: (None if row[c] is None else str(row[c])) for c in cols}
                for row in result]

    def close(self) -> None:  # pragma: no cover - requires live warehouse
        self._client.close()
