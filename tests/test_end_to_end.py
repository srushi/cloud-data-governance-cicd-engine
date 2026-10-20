"""End-to-end tests: full audit on fixtures + CLI + accuracy scoring."""
import json
import os

from engine.audit import run_audit
from engine.cli import main as cli_main
from engine.connectors import get_connector
from engine.models import ExpectedSchema
from engine.reporting import write_reports
from scripts.score_accuracy import score

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(BASE, "fixtures")


def _audit():
    with open(os.path.join(FIXTURES, "expected_schema.json")) as fh:
        schema = ExpectedSchema.from_dict(json.load(fh))
    conn = get_connector("local", fixtures_dir=FIXTURES)
    return run_audit(conn, schema, "local")


def test_audit_finds_exactly_the_planted_issues():
    records, stats = _audit()
    found = {(r.table, r.column, r.check) for r in records}
    assert found == {
        ("orders", "order_id", "duplicate_key"),
        ("customers", "email", "null_rate"),
        ("products", "price", "type_drift"),
        ("events", "event_ts", "freshness"),
        ("inventory", None, "row_count_anomaly"),
        ("payments", "currency", "schema_drift"),
    }
    assert stats["tables_audited"] == 6
    assert stats["rows_scanned"] == 1072


def test_reports_written_and_wellformed(tmp_path):
    records, stats = _audit()
    paths = write_reports(records, stats, str(tmp_path))
    data = json.loads(open(paths["exceptions_json"]).read())
    assert len(data) == 6
    assert all({"table", "check", "severity", "category"} <= set(d) for d in data)
    summary = json.loads(open(paths["summary_json"]).read())
    assert summary["total_exceptions"] == 6
    assert summary["by_severity"]["critical"] == 2


def test_cli_run_audit(tmp_path, monkeypatch):
    monkeypatch.chdir(BASE)
    rc = cli_main(["run-audit", "--source", "local", "--report", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "exceptions.json").exists()
    assert (tmp_path / "exceptions.csv").exists()
    assert (tmp_path / "summary.json").exists()


def test_classifier_accuracy_on_labeled_fixtures(tmp_path):
    records, stats = _audit()
    paths = write_reports(records, stats, str(tmp_path))
    result = score(paths["exceptions_json"],
                   os.path.join(FIXTURES, "expected_exceptions.json"))
    assert result["missed"] == []
    assert result["false_positives"] == []
    assert result["accuracy_percent"] == 100.0
