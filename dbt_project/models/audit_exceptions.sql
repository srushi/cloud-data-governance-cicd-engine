-- Mart: one row per exception written by the Python validation engine
-- (loaded from out/exceptions.json into the warehouse by the deploy job).
-- Keeping exceptions in a dbt model lets dashboards/alerts query them in SQL.
{{ config(materialized='table') }}

select
    table_name,
    column_name,
    check_type,
    category,
    severity,
    message,
    recommended_action,
    detected_at
from {{ source('warehouse', 'engine_exception_log') }}
