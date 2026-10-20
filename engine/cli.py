"""Command-line interface for the validation engine.

Usage::

    python main.py run-audit --source local --report out/
    python -m engine.cli run-audit --source snowflake --report out/
    python main.py score --exceptions out/exceptions.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from .audit import run_audit
from .connectors import get_connector
from .models import ExpectedSchema
from .reporting import write_reports

DEFAULT_SCHEMA = os.path.join("fixtures", "expected_schema.json")
DEFAULT_LABELS = os.path.join("fixtures", "expected_exceptions.json")


def _load_schema(path: str) -> ExpectedSchema:
    with open(path, encoding="utf-8") as fh:
        return ExpectedSchema.from_dict(json.load(fh))


def cmd_run_audit(args: argparse.Namespace) -> int:
    schema = _load_schema(args.schema)
    try:
        connector = get_connector(args.source, fixtures_dir=args.fixtures)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        records, stats = run_audit(connector, schema, args.source)
    finally:
        connector.close()
    paths = write_reports(records, stats, args.report)
    print(f"Audited {stats['tables_audited']} tables, "
          f"{stats['rows_scanned']} rows scanned from source '{args.source}'.")
    print(f"Exceptions found: {len(records)}")
    for rec in records:
        col = f".{rec.column}" if rec.column else ""
        print(f"  [{rec.severity:>8}] {rec.table}{col} :: {rec.check} - {rec.message}")
    print("Reports written:")
    for label, path in paths.items():
        print(f"  {label}: {path}")
    if args.fail_on_critical and any(r.severity == "critical" for r in records):
        print("Failing because critical exceptions were found (--fail-on-critical).")
        return 1
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    from scripts.score_accuracy import score
    result = score(args.exceptions, args.labels)
    print(json.dumps(result, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipeline-engine",
        description="Cloud Data Governance & CI/CD Pipeline Engine")
    sub = parser.add_subparsers(dest="command", required=True)

    audit = sub.add_parser("run-audit", help="Audit a warehouse and write reports")
    audit.add_argument("--source", default="local",
                       choices=["local", "snowflake", "bigquery"],
                       help="Data source to audit (default: local)")
    audit.add_argument("--fixtures", default="fixtures",
                       help="Fixture directory for the local source")
    audit.add_argument("--schema", default=DEFAULT_SCHEMA,
                       help="Expected-schema JSON path")
    audit.add_argument("--report", default="out", help="Output report directory")
    audit.add_argument("--fail-on-critical", action="store_true",
                       help="Exit 1 when critical exceptions are found")
    audit.set_defaults(func=cmd_run_audit)

    score = sub.add_parser("score", help="Score exceptions against labeled fixtures")
    score.add_argument("--exceptions", default=os.path.join("out", "exceptions.json"))
    score.add_argument("--labels", default=DEFAULT_LABELS)
    score.set_defaults(func=cmd_score)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
