select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    

with all_values as (

    select
        source as value_field,
        count(*) as n_records

    from "db"."public_staging"."stg_sessions"
    group by source

)

select *
from all_values
where value_field not in (
    'google','direct','facebook','linkedin','newsletter','referral','bing'
)



      
    ) dbt_internal_test