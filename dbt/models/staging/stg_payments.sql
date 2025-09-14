with src as (
  select * from raw.payments
), success as (
  select *, (amount - coalesce(fee,0) - coalesce(refunded_amount,0))::numeric as net_revenue
  from src
  where status = 'succeeded'
)
select
  payment_id,
  customer_id,
  product,
  amount,
  currency,
  status,
  refunded_amount,
  fee,
  payment_method,
  country,
  created_at::timestamp as created_at,
  updated_at::timestamp as updated_at,
  net_revenue,
  date_trunc('day', created_at)::date as order_day
from success