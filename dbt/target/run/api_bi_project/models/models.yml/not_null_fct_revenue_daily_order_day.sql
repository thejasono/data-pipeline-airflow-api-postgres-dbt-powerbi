select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select order_day
from "db"."_analytics"."fct_revenue_daily"
where order_day is null



      
    ) dbt_internal_test