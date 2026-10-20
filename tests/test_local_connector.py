"""Tests for the local CSV connector and connector factory errors."""
import pytest

from engine.connectors import get_connector
from engine.connectors.local_connector import LocalConnector

FIXTURES = "fixtures"


def test_lists_all_fixture_tables():
    conn = LocalConnector(FIXTURES)
    assert conn.list_tables() == ["customers", "events", "inventory",
                                  "orders", "payments", "products"]


def test_fetch_table_rows_and_null_handling():
    conn = LocalConnector(FIXTURES)
    rows = conn.fetch_table("customers")
    assert len(rows) == 150
    assert any(r["email"] is None for r in rows)  # empty CSV cell -> None


def test_table_columns_come_from_header():
    conn = LocalConnector(FIXTURES)
    cols = conn.table_columns("payments")
    assert cols[0] == "payment_id"
    assert "currency" not in cols  # the planted schema drift


def test_cloud_connectors_fail_clearly_without_credentials(monkeypatch):
    for var in ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
                "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA",
                "BIGQUERY_PROJECT", "BIGQUERY_DATASET"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(RuntimeError):
        get_connector("snowflake")
    with pytest.raises(RuntimeError):
        get_connector("bigquery")


def test_unknown_source_rejected():
    with pytest.raises(ValueError):
        get_connector("oracle")
