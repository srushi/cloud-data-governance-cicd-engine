"""Data-quality validation rules.

Each check inspects one table (a list of row dicts, values as strings or
``None``) against its :class:`~engine.models.TableSpec` and returns a list of
:class:`~engine.models.Finding` objects. Checks are pure functions so they can
be unit-tested without any warehouse connection.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Optional

from .models import Finding, TableSpec

_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(r"^[+-]?(\d+\.\d*|\.\d+|\d+)([eE][+-]?\d+)?$")


def is_null(value: Any) -> bool:
    """A value is null when it is None or an empty/whitespace string."""
    return value is None or (isinstance(value, str) and value.strip() == "")


def parse_datetime(value: str) -> Optional[datetime]:
    text = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def infer_value_type(value: str) -> str:
    """Infer the type of a single non-null string value."""
    text = value.strip()
    if text.lower() in ("true", "false"):
        return "BOOLEAN"
    if _INT_RE.match(text):
        return "INTEGER"
    if _FLOAT_RE.match(text):
        return "FLOAT"
    dt = parse_datetime(text)
    if dt is not None:
        return "TIMESTAMP" if ("T" in text or " " in text) else "DATE"
    return "STRING"


def type_compatible(expected: str, inferred: str) -> bool:
    if expected == inferred:
        return True
    if expected == "FLOAT" and inferred == "INTEGER":
        return True
    if expected == "TIMESTAMP" and inferred == "DATE":
        return True
    if expected == "DATE" and inferred == "TIMESTAMP":
        return True
    return False


def check_schema_drift(table: str, spec: TableSpec, actual_columns: list[str]) -> list[Finding]:
    findings = []
    expected = [c.name for c in spec.columns]
    for col in expected:
        if col not in actual_columns:
            findings.append(Finding(
                table=table, column=col, check="schema_drift",
                message=f"Expected column '{col}' is missing from table '{table}'.",
                metrics={"expected_type": spec.column(col).type},
            ))
    for col in actual_columns:
        if col not in expected:
            findings.append(Finding(
                table=table, column=col, check="schema_drift",
                message=f"Unexpected column '{col}' present in table '{table}'.",
                metrics={"direction": "extra_column"},
            ))
    return findings


def check_null_rates(table: str, rows: list[dict], spec: TableSpec,
                     present: Optional[set] = None) -> list[Finding]:
    findings = []
    if not rows:
        return findings
    total = len(rows)
    for col in spec.columns:
        if present is not None and col.name not in present:
            continue  # missing columns are reported by schema_drift, not null_rate
        nulls = sum(1 for r in rows if is_null(r.get(col.name)))
        rate = nulls / total
        if rate > col.max_null_rate:
            findings.append(Finding(
                table=table, column=col.name, check="null_rate",
                message=(f"Column '{col.name}' null rate {rate:.1%} exceeds "
                         f"threshold {col.max_null_rate:.1%} ({nulls}/{total} rows)."),
                metrics={"null_count": nulls, "row_count": total,
                         "null_rate": round(rate, 4), "threshold": col.max_null_rate},
            ))
    return findings


def check_type_drift(table: str, rows: list[dict], spec: TableSpec,
                     mismatch_threshold: float = 0.20,
                     present: Optional[set] = None) -> list[Finding]:
    findings = []
    for col in spec.columns:
        if present is not None and col.name not in present:
            continue  # missing columns are reported by schema_drift
        values = [str(r.get(col.name)) for r in rows if not is_null(r.get(col.name))]
        if not values:
            continue
        inferred = [infer_value_type(v) for v in values]
        mismatched = sum(1 for t in inferred if not type_compatible(col.type, t))
        fraction = mismatched / len(values)
        if fraction > mismatch_threshold:
            dominant = Counter(inferred).most_common(1)[0][0]
            findings.append(Finding(
                table=table, column=col.name, check="type_drift",
                message=(f"Column '{col.name}' expected {col.type} but dominant "
                         f"inferred type is {dominant} ({fraction:.1%} of values mismatch)."),
                metrics={"expected_type": col.type, "dominant_inferred_type": dominant,
                         "mismatch_fraction": round(fraction, 4),
                         "sampled_values": len(values)},
            ))
    return findings


def check_duplicate_keys(table: str, rows: list[dict], spec: TableSpec) -> list[Finding]:
    findings = []
    if len(spec.primary_key) != 1:
        return findings
    key = spec.primary_key[0]
    counts = Counter(str(r.get(key)) for r in rows if not is_null(r.get(key)))
    dup_keys = {k: c for k, c in counts.items() if c > 1}
    if dup_keys:
        findings.append(Finding(
            table=table, column=key, check="duplicate_key",
            message=(f"Primary key '{key}' has {len(dup_keys)} duplicated value(s) "
                     f"covering {sum(dup_keys.values())} rows."),
            metrics={"duplicate_key_count": len(dup_keys),
                     "sample_duplicate_keys": sorted(dup_keys)[:10]},
        ))
    return findings


def check_freshness(table: str, rows: list[dict], spec: TableSpec,
                    reference_time: datetime) -> list[Finding]:
    if not spec.freshness_column or spec.freshness_max_age_hours is None:
        return []
    col = spec.freshness_column
    stamps = [parse_datetime(str(r.get(col))) for r in rows if not is_null(r.get(col))]
    stamps = [s for s in stamps if s is not None]
    if not stamps:
        return []
    latest = max(stamps)
    age_hours = (reference_time - latest).total_seconds() / 3600.0
    if age_hours > spec.freshness_max_age_hours:
        return [Finding(
            table=table, column=col, check="freshness",
            message=(f"Table '{table}' is stale: latest {col}={latest.isoformat()} "
                     f"is {age_hours:.1f}h old (max {spec.freshness_max_age_hours}h)."),
            metrics={"latest_value": latest.isoformat(),
                     "age_hours": round(age_hours, 2),
                     "max_age_hours": spec.freshness_max_age_hours},
        )]
    return []


def check_row_count(table: str, rows: list[dict], spec: TableSpec) -> list[Finding]:
    count = len(rows)
    too_low = spec.row_count_min is not None and count < spec.row_count_min
    too_high = spec.row_count_max is not None and count > spec.row_count_max
    if too_low or too_high:
        return [Finding(
            table=table, column=None, check="row_count_anomaly",
            message=(f"Table '{table}' row count {count} is outside expected range "
                     f"[{spec.row_count_min}, {spec.row_count_max}]."),
            metrics={"row_count": count, "expected_min": spec.row_count_min,
                     "expected_max": spec.row_count_max},
        )]
    return []


def run_all_checks(table: str, rows: list[dict], actual_columns: list[str],
                   spec: TableSpec, reference_time: datetime) -> list[Finding]:
    """Run every check for one table and return all findings."""
    findings: list[Finding] = []
    present = set(actual_columns)
    findings += check_schema_drift(table, spec, actual_columns)
    findings += check_null_rates(table, rows, spec, present=present)
    findings += check_type_drift(table, rows, spec, present=present)
    findings += check_duplicate_keys(table, rows, spec)
    findings += check_freshness(table, rows, spec, reference_time)
    findings += check_row_count(table, rows, spec)
    return findings
