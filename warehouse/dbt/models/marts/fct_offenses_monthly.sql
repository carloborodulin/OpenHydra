-- One row per level/area/offense/month, pivoting the long series/measure rows
-- into offense & clearance columns, plus a derived clearance ratio.
with s as (
    select * from {{ ref('stg_summarized') }}
)

select
    level,
    area,
    offense,
    period,
    max(case when series = 'offenses'   and measure = 'rate'   then value end) as offenses_rate,
    max(case when series = 'offenses'   and measure = 'actual' then value end) as offenses_actual,
    max(case when series = 'clearances' and measure = 'rate'   then value end) as clearances_rate,
    max(case when series = 'clearances' and measure = 'actual' then value end) as clearances_actual,
    max(case when series = 'clearances' and measure = 'actual' then value end)
        / nullif(max(case when series = 'offenses' and measure = 'actual' then value end), 0)
        as clearance_ratio
from s
group by level, area, offense, period
