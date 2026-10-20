"""Unit tests for the individual validation rules."""
from datetime import datetime, timezone

from engine import checks
from engine.models import ColumnSpec, ExpectedSchema, TableSpec

REF = datetime(2026, 10, 20, tzinfo=timezone.utc)


def spec(**kw) -> TableSpec:
    base = dict(
        name="t",
        columns=[ColumnSpec("id", "INTEGER", 0.0),
                 ColumnSpec("email", "STRING", 0.05),
                 ColumnSpec("amount", "FLOAT", 0.02)],
        primary_key=["id"],
    )
    base.update(kw)
    return TableSpec(**base)


def test_null_rate_flags_column_above_threshold():
    rows = [{"id": str(i), "email": "" if i < 3 else "a@b.c", "amount": "1.5"}
            for i in range(10)]  # email 30% null > 5%
    findings = checks.check_null_rates("t", rows, spec(), present={"id", "email", "amount"})
    assert [f.column for f in findings] == ["email"]


def test_null_rate_clean_below_threshold():
    rows = [{"id": str(i), "email": "a@b.c", "amount": "1.5"} for i in range(10)]
    assert checks.check_null_rates("t", rows, spec()) == []


def test_missing_column_not_double_reported_as_nulls():
    rows = [{"id": "1", "amount": "2.0"}]  # email column absent entirely
    out = checks.check_null_rates("t", rows, spec(), present={"id", "amount"})
    assert out == []


def test_type_drift_detects_string_in_float_column():
    rows = [{"id": str(i), "email": "a@b.c", "amount": "N/A" if i < 7 else "9.99"}
            for i in range(10)]
    findings = checks.check_type_drift("t", rows, spec(), present={"id", "email", "amount"})
    assert len(findings) == 1
    assert findings[0].column == "amount"
    assert findings[0].metrics["dominant_inferred_type"] == "STRING"


def test_type_compatibility_rules():
    assert checks.type_compatible("FLOAT", "INTEGER")
    assert checks.type_compatible("INTEGER", "INTEGER")
    assert not checks.type_compatible("FLOAT", "STRING")


def test_infer_value_type():
    assert checks.infer_value_type("42") == "INTEGER"
    assert checks.infer_value_type("4.25") == "FLOAT"
    assert checks.infer_value_type("true") == "BOOLEAN"
    assert checks.infer_value_type("2026-10-19") == "DATE"
    assert checks.infer_value_type("2026-10-19T08:00:00") == "TIMESTAMP"
    assert checks.infer_value_type("hello") == "STRING"


def test_duplicate_keys():
    rows = [{"id": "1"}, {"id": "2"}, {"id": "2"}, {"id": "3"}]
    findings = checks.check_duplicate_keys("t", rows, spec())
    assert len(findings) == 1
    assert findings[0].metrics["duplicate_key_count"] == 1


def test_freshness_stale_and_fresh():
    stale_spec = spec(freshness_column="email", freshness_max_age_hours=72)
    rows = [{"email": "2026-09-01T00:00:00"}]
    out = checks.check_freshness("t", rows, stale_spec, REF)
    assert len(out) == 1 and out[0].check == "freshness"
    fresh_spec = spec(freshness_column="email", freshness_max_age_hours=7200)
    assert checks.check_freshness("t", rows, fresh_spec, REF) == []


def test_row_count_anomaly_bounds():
    s = spec(row_count_min=10, row_count_max=20)
    assert checks.check_row_count("t", [{}] * 5, s)[0].check == "row_count_anomaly"
    assert checks.check_row_count("t", [{}] * 15, s) == []
    assert checks.check_row_count("t", [{}] * 25, s)[0].check == "row_count_anomaly"


def test_schema_drift_missing_and_extra():
    findings = checks.check_schema_drift("t", spec(), ["id", "email", "surprise"])
    kinds = {(f.column, f.check) for f in findings}
    assert ("amount", "schema_drift") in kinds
    assert ("surprise", "schema_drift") in kinds


def test_expected_schema_from_dict():
    raw = {"reference_time": "2026-10-20T00:00:00Z",
           "tables": {"t": {"columns": [{"name": "id", "type": "integer"}],
                            "primary_key": ["id"],
                            "freshness": {"column": "id", "max_age_hours": 5},
                            "row_count": {"min": 1, "max": 9}}}}
    schema = ExpectedSchema.from_dict(raw)
    t = schema.tables["t"]
    assert t.columns[0].type == "INTEGER"
    assert t.freshness_max_age_hours == 5
    assert t.row_count_min == 1 and t.row_count_max == 9
