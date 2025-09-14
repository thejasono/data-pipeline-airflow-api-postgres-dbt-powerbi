with c as (
  select * from {{ ref('stg_customers') }}
)
select
  customer_id,
  company_name,
  country,
  industry,
  company_size,
  signup_date,
  is_churned,
  signup_month
from c