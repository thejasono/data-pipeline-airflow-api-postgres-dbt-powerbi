
  
    

  create  table "db"."public_analytics"."dim_customer__dbt_tmp"
  
  
    as
  
  (
    with c as (
  select * from "db"."public_staging"."stg_customers"
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
  );
  