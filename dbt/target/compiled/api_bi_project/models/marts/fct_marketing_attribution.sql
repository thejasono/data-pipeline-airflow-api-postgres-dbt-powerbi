with s as (
  select * from "db"."public_staging"."stg_sessions"
)
select
  session_day,
  source,
  medium,
  coalesce(campaign,'') as campaign,
  sum(converted::int) as conversions,
  avg((not bounced)::int)::float as engagement_rate
from s
group by 1,2,3,4