"""Connector factory."""

from __future__ import annotations

from .base import WarehouseConnector
from .local_connector import LocalConnector

__all__ = ["WarehouseConnector", "LocalConnector", "get_connector"]


def get_connector(source: str, fixtures_dir: str = "fixtures") -> WarehouseConnector:
    """Build the connector for ``source`` (local | snowflake | bigquery)."""
    if source == "local":
        return LocalConnector(fixtures_dir)
    if source == "snowflake":
        from .snowflake_connector import SnowflakeConnector
        return SnowflakeConnector()
    if source == "bigquery":
        from .bigquery_connector import BigQueryConnector
        return BigQueryConnector()
    raise ValueError(f"Unknown source: {source!r} (expected local|snowflake|bigquery)")
