with src as (
  select * from raw.sessions
)
select
  session_id,
  nullif(customer_id::text,'')::uuid as customer_id,
  lower(source) as source,
  lower(medium) as medium,
  campaign,
  lower(device) as device,
  country,
  pageviews,
  session_duration_s,
  (bounced=1) as bounced,
  (converted=1) as converted,
  session_start::timestamp as session_start,
  updated_at::timestamp as updated_at,
  date_trunc('day', session_start)::date as session_day
from src