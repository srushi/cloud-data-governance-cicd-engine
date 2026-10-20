"""Tests for severity classification."""
from engine.classifier import classify
from engine.models import Finding


def f(check, **metrics):
    return Finding(table="t", column="c", check=check, message="m", metrics=metrics)


def test_duplicate_key_is_critical():
    assert classify(f("duplicate_key")).severity == "critical"
    assert classify(f("duplicate_key")).category == "uniqueness"


def test_schema_drift_is_high():
    rec = classify(f("schema_drift"))
    assert rec.severity == "high"
    assert rec.category == "schema_conformance"


def test_null_rate_severity_scales_with_rate():
    assert classify(f("null_rate", null_rate=0.30, threshold=0.05)).severity == "high"
    assert classify(f("null_rate", null_rate=0.06, threshold=0.05)).severity == "medium"


def test_freshness_severity_scales_with_age():
    assert classify(f("freshness", age_hours=1000, max_age_hours=72)).severity == "critical"
    assert classify(f("freshness", age_hours=100, max_age_hours=72)).severity == "high"


def test_type_drift_severity():
    assert classify(f("type_drift", mismatch_fraction=0.6)).severity == "medium"
    assert classify(f("type_drift", mismatch_fraction=0.9)).severity == "high"


def test_row_count_severity():
    rec = classify(f("row_count_anomaly", row_count=120, expected_min=500,
                     expected_max=5000))
    assert rec.severity == "high"
    rec2 = classify(f("row_count_anomaly", row_count=450, expected_min=500,
                      expected_max=5000))
    assert rec2.severity == "medium"


def test_every_record_has_action_and_category():
    for check in ("null_rate", "type_drift", "schema_drift", "duplicate_key",
                  "freshness", "row_count_anomaly"):
        rec = classify(f(check))
        assert rec.recommended_action
        assert rec.category != "data_quality"
