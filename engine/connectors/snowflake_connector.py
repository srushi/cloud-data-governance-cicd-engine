"""Snowflake connector (real client library).

Uses ``snowflake-connector-python`` when it is installed and the standard
``SNOWFLAKE_*`` environment variables are present::

    SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD,
    SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA

When credentials or the library are missing, construction raises a clear
``RuntimeError`` — the audit CLI then suggests ``--source local`` for the
offline demo. Nothing about this connector is mocked: with real credentials
it queries INFORMATION_SCHEMA / the tables directly.
"""

from __future__ import annotations

import os

from .base import WarehouseConnector

REQUIRED_ENV = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
                "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA"]


class SnowflakeConnector(WarehouseConnector):
    name = "snowflake"

    def __init__(self):
        missing = [v for v in REQUIRED_ENV if not os.environ.get(v)]
        if missing:
            raise RuntimeError(
                "Snowflake credentials missing (env vars: "
                + ", ".join(missing) + "). Use --source local for the offline demo.")
        try:
            import snowflake.connector  # noqa: F401
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "snowflake-connector-python is not installed; "
                "install requirements-connectors.txt") from exc
        self._conn = snowflake.connector.connect(
            account=os.environ["SNOWFLAKE_ACCOUNT"],
            user=os.environ["SNOWFLAKE_USER"],
            password=os.environ["SNOWFLAKE_PASSWORD"],
            warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE"),
            database=os.environ["SNOWFLAKE_DATABASE"],
            schema=os.environ["SNOWFLAKE_SCHEMA"],
        )
        self._schema = os.environ["SNOWFLAKE_SCHEMA"]
        self._columns_cache: dict[str, list[str]] = {}

    def _query(self, sql: str, params: tuple = ()) -> list[tuple]:
        cur = self._conn.cursor()
        try:
            cur.execute(sql, params)
            return cur.fetchall()
        finally:
            cur.close()

    def list_tables(self) -> list[str]:
        rows = self._query(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = %s ORDER BY table_name", (self._schema,))
        return [str(r[0]).lower() for r in rows]

    def table_columns(self, table: str) -> list[str]:
        if table not in self._columns_cache:
            rows = self._query(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = %s "
                "ORDER BY ordinal_position", (self._schema, table.upper()))
            self._columns_cache[table] = [str(r[0]).lower() for r in rows]
        return self._columns_cache[table]

    def fetch_table(self, table: str) -> list[dict]:
        cols = self.table_columns(table)
        if not cols:
            return []
        col_sql = ", ".join(f'"{c}"' for c in cols)
        rows = self._query(f'SELECT {col_sql} FROM "{table}"')
        return [{c: (None if v is None else str(v)) for c, v in zip(cols, row)}
                for row in rows]

    def close(self) -> None:  # pragma: no cover - requires live warehouse
        self._conn.close()
