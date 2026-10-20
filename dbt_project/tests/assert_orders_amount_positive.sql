-- Singular test: order amounts must never be negative.
select order_id, amount
from {{ ref('stg_orders') }}
where amount < 0
