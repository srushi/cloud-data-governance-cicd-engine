"""Exception classifier.

Turns raw :class:`~engine.models.Finding` objects into classified
:class:`~engine.models.ExceptionRecord` objects: each exception gets a
category, a severity (critical / high / medium / low) derived from the
finding's metrics, and a recommended remediation action. This is the
component whose accuracy is measured against the labeled fixtures by
``scripts/score_accuracy.py``.
"""

from __future__ import annotations

from .models import ExceptionRecord, Finding

CATEGORIES = {
    "null_rate": "completeness",
    "type_drift": "schema_conformance",
    "schema_drift": "schema_conformance",
    "duplicate_key": "uniqueness",
    "freshness": "timeliness",
    "row_count_anomaly": "volume",
}

ACTIONS = {
    "null_rate": "Investigate upstream producer; backfill or reject null rows at ingestion.",
    "type_drift": "Quarantine mismatched values; align source contract with the warehouse schema.",
    "schema_drift": "Reconcile the deployed schema with the expected contract; update dbt models.",
    "duplicate_key": "Deduplicate on the primary key and add a uniqueness constraint upstream.",
    "freshness": "Check the ingestion schedule/ DAG run; replay the missed load window.",
    "row_count_anomaly": "Compare against source-system counts; check for partial or double loads.",
}


def _severity(finding: Finding) -> str:
    m = finding.metrics
    if finding.check == "duplicate_key":
        return "critical"
    if finding.check == "schema_drift":
        return "high"
    if finding.check == "null_rate":
        rate = float(m.get("null_rate", 0))
        threshold = float(m.get("threshold", 0))
        return "high" if rate >= max(2 * threshold, threshold + 0.10) else "medium"
    if finding.check == "type_drift":
        frac = float(m.get("mismatch_fraction", 0))
        return "high" if frac > 0.75 else "medium"
    if finding.check == "freshness":
        age = float(m.get("age_hours", 0))
        limit = float(m.get("max_age_hours", 1))
        return "critical" if age > 4 * limit else "high"
    if finding.check == "row_count_anomaly":
        count = float(m.get("row_count", 0))
        low = m.get("expected_min")
        high = m.get("expected_max")
        if low and count < 0.5 * float(low):
            return "high"
        if high and count > 2 * float(high):
            return "high"
        return "medium"
    return "low"


def classify(finding: Finding) -> ExceptionRecord:
    """Classify a single finding into an exception record."""
    return ExceptionRecord(
        table=finding.table,
        column=finding.column,
        check=finding.check,
        category=CATEGORIES.get(finding.check, "data_quality"),
        severity=_severity(finding),
        message=finding.message,
        recommended_action=ACTIONS.get(finding.check, "Investigate the finding."),
        metrics=finding.metrics,
    )


def classify_all(findings: list[Finding]) -> list[ExceptionRecord]:
    records = [classify(f) for f in findings]
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return sorted(records, key=lambda r: (order.get(r.severity, 4), r.table, r.check))
