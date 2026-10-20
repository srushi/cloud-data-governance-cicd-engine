-- Staging model for the audited `inventory` warehouse table.
-- The Python engine audits these same tables; dbt tests in schema.yml
-- enforce the contract at build time.
select *
from {{ source('warehouse', 'inventory') }}
