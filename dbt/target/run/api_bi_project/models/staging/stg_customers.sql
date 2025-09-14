
  create view "db"."public_staging"."stg_customers__dbt_tmp"
    
    
  as (
    with src as (
  select * from raw.customers
)
select
  customer_id,
  company_name,
  country,
  industry,
  company_size,
  signup_date::timestamp as signup_date,
  updated_at::timestamp as updated_at,
  is_churned::boolean as is_churned,
  date_trunc('month', signup_date)::date as signup_month
from src
  );