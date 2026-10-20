"""Report writers: structured exception log (JSON + CSV) and a summary."""

from __future__ import annotations

import csv
import json
import os
from collections import Counter
from typing import Any

from .models import ExceptionRecord

CSV_FIELDS = ["table", "column", "check", "category", "severity",
              "message", "recommended_action"]


def summarize(records: list[ExceptionRecord], stats: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": stats.get("source"),
        "tables_audited": stats.get("tables_audited", 0),
        "rows_scanned": stats.get("rows_scanned", 0),
        "total_exceptions": len(records),
        "by_severity": dict(Counter(r.severity for r in records)),
        "by_check": dict(Counter(r.check for r in records)),
        "by_category": dict(Counter(r.category for r in records)),
        "by_table": dict(Counter(r.table for r in records)),
    }


def write_reports(records: list[ExceptionRecord], stats: dict[str, Any],
                  out_dir: str) -> dict[str, str]:
    """Write exceptions.json, exceptions.csv and summary.json to ``out_dir``."""
    os.makedirs(out_dir, exist_ok=True)
    paths = {
        "exceptions_json": os.path.join(out_dir, "exceptions.json"),
        "exceptions_csv": os.path.join(out_dir, "exceptions.csv"),
        "summary_json": os.path.join(out_dir, "summary.json"),
    }
    with open(paths["exceptions_json"], "w", encoding="utf-8") as fh:
        json.dump([r.to_dict() for r in records], fh, indent=2)
    with open(paths["exceptions_csv"], "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for r in records:
            row = {k: getattr(r, k) for k in CSV_FIELDS}
            row["column"] = r.column or ""
            writer.writerow(row)
    with open(paths["summary_json"], "w", encoding="utf-8") as fh:
        json.dump(summarize(records, stats), fh, indent=2)
    return paths
