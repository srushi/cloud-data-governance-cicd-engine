-- Staging model for the audited `customers` warehouse table.
-- The Python engine audits these same tables; dbt tests in schema.yml
-- enforce the contract at build time.
select *
from {{ source('warehouse', 'customers') }}
