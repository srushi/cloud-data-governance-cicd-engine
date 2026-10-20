"""Audit orchestration: fetch tables, run checks, classify findings."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import checks
from .classifier import classify_all
from .connectors.base import WarehouseConnector
from .models import ExceptionRecord, ExpectedSchema


def _reference_time(schema: ExpectedSchema) -> datetime:
    if schema.reference_time:
        parsed = checks.parse_datetime(schema.reference_time)
        if parsed is not None:
            return parsed
    return datetime.now(timezone.utc)


def run_audit(connector: WarehouseConnector, schema: ExpectedSchema,
              source_name: str) -> tuple[list[ExceptionRecord], dict[str, Any]]:
    """Audit every table in the expected schema.

    Tables missing from the warehouse are reported through the row-count and
    schema checks rather than crashing the audit.
    """
    reference = _reference_time(schema)
    all_findings = []
    rows_scanned = 0
    tables_audited = 0
    available = set(connector.list_tables())
    for name, spec in schema.tables.items():
        tables_audited += 1
        if name in available:
            rows = connector.fetch_table(name)
            actual_columns = connector.table_columns(name)
        else:
            rows, actual_columns = [], []
        rows_scanned += len(rows)
        all_findings += checks.run_all_checks(name, rows, actual_columns, spec, reference)
    records = classify_all(all_findings)
    stats = {"source": source_name, "tables_audited": tables_audited,
             "rows_scanned": rows_scanned}
    return records, stats
