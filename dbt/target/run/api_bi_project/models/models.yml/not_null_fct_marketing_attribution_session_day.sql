select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select session_day
from "db"."_analytics"."fct_marketing_attribution"
where session_day is null



      
    ) dbt_internal_test