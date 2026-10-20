"""Core data models for the validation engine.

The expected warehouse schema is described by a JSON document (see
``fixtures/expected_schema.json``) with this shape::

    {
      "reference_time": "2026-10-20T00:00:00Z",
      "tables": {
        "<table>": {
          "columns": [{"name": "id", "type": "INTEGER", "max_null_rate": 0.0}],
          "primary_key": ["id"],
          "freshness": {"column": "updated_at", "max_age_hours": 72},
          "row_count": {"min": 100, "max": 100000}
        }
      }
    }
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class ColumnSpec:
    name: str
    type: str  # INTEGER | FLOAT | STRING | BOOLEAN | DATE | TIMESTAMP
    max_null_rate: float = 0.0


@dataclass
class TableSpec:
    name: str
    columns: list[ColumnSpec]
    primary_key: list[str] = field(default_factory=list)
    freshness_column: Optional[str] = None
    freshness_max_age_hours: Optional[float] = None
    row_count_min: Optional[int] = None
    row_count_max: Optional[int] = None

    def column(self, name: str) -> Optional[ColumnSpec]:
        for col in self.columns:
            if col.name == name:
                return col
        return None


@dataclass
class ExpectedSchema:
    reference_time: Optional[str]
    tables: dict[str, TableSpec]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ExpectedSchema":
        tables: dict[str, TableSpec] = {}
        for tname, tspec in raw.get("tables", {}).items():
            cols = [
                ColumnSpec(
                    name=c["name"],
                    type=str(c["type"]).upper(),
                    max_null_rate=float(c.get("max_null_rate", 0.0)),
                )
                for c in tspec.get("columns", [])
            ]
            fresh = tspec.get("freshness") or {}
            rows = tspec.get("row_count") or {}
            tables[tname] = TableSpec(
                name=tname,
                columns=cols,
                primary_key=list(tspec.get("primary_key", [])),
                freshness_column=fresh.get("column"),
                freshness_max_age_hours=fresh.get("max_age_hours"),
                row_count_min=rows.get("min"),
                row_count_max=rows.get("max"),
            )
        return cls(reference_time=raw.get("reference_time"), tables=tables)


@dataclass
class Finding:
    """A raw detection produced by a check, before classification."""

    table: str
    column: Optional[str]
    check: str  # null_rate | type_drift | freshness | duplicate_key |
    #             row_count_anomaly | schema_drift
    message: str
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExceptionRecord:
    """A classified data-quality exception (one row of the exception log)."""

    table: str
    column: Optional[str]
    check: str
    category: str
    severity: str  # critical | high | medium | low
    message: str
    recommended_action: str
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
