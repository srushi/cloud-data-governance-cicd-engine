# Fixtures

Offline warehouse used by `--source local`:

- `*.csv` — one file per warehouse table (orders, customers, products,
  events, inventory, payments), generated deterministically by
  `scripts/generate_fixtures.py` (seed 42).
- `expected_schema.json` — the contract the engine audits against: column
  types, null-rate thresholds, primary keys, freshness windows and expected
  row-count ranges. `reference_time` pins "now" so runs are reproducible.
- `expected_exceptions.json` — labeled ground truth: the six data-quality
  issues planted in the CSVs. `scripts/score_accuracy.py` measures how many
  of them the engine finds (and whether it invents any others).
