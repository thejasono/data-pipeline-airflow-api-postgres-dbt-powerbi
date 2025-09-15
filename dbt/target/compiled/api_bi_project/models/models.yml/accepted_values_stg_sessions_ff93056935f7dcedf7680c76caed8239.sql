
    
    

with all_values as (

    select
        source as value_field,
        count(*) as n_records

    from "db"."_staging"."stg_sessions"
    group by source

)

select *
from all_values
where value_field not in (
    'google','direct','facebook','linkedin','newsletter','referral','bing'
)


