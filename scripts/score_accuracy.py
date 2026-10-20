#!/usr/bin/env python3
"""Score detected exceptions against the labeled fixture ground truth.

A label ``{table, column, check}`` is a hit when the exception log contains
an entry with the same table, check, and column (null column matches a
null/empty one). Accuracy reported here is label recall (planted issues
found / planted issues) — plus precision so false positives are visible too.

Usage:
    python scripts/score_accuracy.py --exceptions out/exceptions.json
    python main.py score
"""

from __future__ import annotations

import argparse
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _key(entry: dict) -> tuple:
    return (entry.get("table"), entry.get("column") or None, entry.get("check"))


def score(exceptions_path: str, labels_path: str) -> dict:
    with open(exceptions_path, encoding="utf-8") as fh:
        detected = {_key(e) for e in json.load(fh)}
    with open(labels_path, encoding="utf-8") as fh:
        labels = {_key(e) for e in json.load(fh)}
    hits = labels & detected
    missed = sorted(labels - detected)
    false_positives = sorted(detected - labels)
    total = len(labels)
    accuracy = (len(hits) / total) if total else 1.0
    precision = (len(hits) / len(detected)) if detected else 0.0
    return {
        "planted_issues": total,
        "detected_issues": len(detected),
        "correctly_classified": len(hits),
        "accuracy_recall": round(accuracy, 4),
        "accuracy_percent": round(accuracy * 100, 2),
        "precision": round(precision, 4),
        "missed": [list(m) for m in missed],
        "false_positives": [list(f) for f in false_positives],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score classifier accuracy")
    parser.add_argument("--exceptions", default=os.path.join(BASE, "out", "exceptions.json"))
    parser.add_argument("--labels", default=os.path.join(BASE, "fixtures",
                                                         "expected_exceptions.json"))
    args = parser.parse_args()
    print(json.dumps(score(args.exceptions, args.labels), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
