select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select country
from "db"."_staging"."stg_customers"
where country is null



      
    ) dbt_internal_test