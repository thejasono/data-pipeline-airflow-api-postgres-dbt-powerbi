with p as (
  select * from "db"."public_staging"."stg_payments"
)
select
  order_day,
  product,
  country,
  sum(net_revenue) as net_revenue,
  count(*) as orders
from p
group by 1,2,3