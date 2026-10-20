# dbt project: warehouse_audit

Models the same warehouse tables the Python engine audits, so the contract
is enforced twice: by dbt tests at build time and by the engine's scheduled
audits in production.

- `models/stg_*.sql` — staging models over the raw warehouse sources
- `models/audit_exceptions.sql` — mart over the engine's exception log
- `models/schema.yml` — generic tests: `unique`, `not_null`,
  `accepted_values`, `relationships`
- `tests/` — singular SQL tests

Run with a real warehouse profile (see `profiles.yml.example`):

```bash
pip install dbt-snowflake   # or dbt-bigquery
dbt build
```
