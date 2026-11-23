-- One row per level/area/offense/month: offense and clearance columns, the
-- clearance ratio, and the trend metrics below.
--
-- Trend definitions (one policy for the dashboard and the notebook):
--   ttm_months  The number of months with a rate in the 12 calendar months that
--               end at this month (a missing month is not replaced).
--   ttm_rate    The mean monthly rate over those 12 calendar months. It is null
--               unless all 12 months have a rate, so a partial window (the first
--               11 months of the series, or a gap) never looks like a full year.
--   yoy_delta   ttm_rate / ttm_rate of the same month one year before, minus 1.
--   index_2019  ttm_rate / (mean monthly rate of calendar 2019) x 100. The
--               baseline needs all 12 months of 2019. December 2019 is 100.
with s as (
    select * from {{ ref('stg_summarized') }}
),

pivoted as (
    select
        level,
        area,
        offense,
        period,
        max(case when series = 'offenses' and measure = 'rate' then value end) as offenses_rate,
        max(case when series = 'offenses' and measure = 'actual' then value end) as offenses_actual,
        max(case when series = 'clearances' and measure = 'rate' then value end) as clearances_rate,
        max(case when series = 'clearances' and measure = 'actual' then value end) as clearances_actual,
        max(case when series = 'clearances' and measure = 'actual' then value end)
            / nullif(max(case when series = 'offenses' and measure = 'actual' then value end), 0)
            as clearance_ratio
    from s
    group by level, area, offense, period
),

-- A RANGE window over the date, not a ROWS window: a missing month makes the
-- window hold 11 months instead of silently reaching back 13 months.
windowed as (
    select
        *,
        avg(offenses_rate) over w as ttm_mean,
        count(offenses_rate) over w as ttm_months
    from pivoted
    window w as (
        partition by level, area, offense
        order by period
        range between interval 11 month preceding and current row
    )
),

ttm as (
    select
        * exclude (ttm_mean),
        case when ttm_months = 12 then ttm_mean end as ttm_rate
    from windowed
),

baseline_2019 as (
    select level, area, offense, avg(offenses_rate) as base_2019
    from pivoted
    where year(period) = 2019
    group by level, area, offense
    having count(offenses_rate) = 12
)

select
    t.level,
    t.area,
    t.offense,
    t.period,
    t.offenses_rate,
    t.offenses_actual,
    t.clearances_rate,
    t.clearances_actual,
    t.clearance_ratio,
    t.ttm_months,
    t.ttm_rate,
    -- Date join (not lag(12)) so it stays correct if a month is missing.
    t.ttm_rate / nullif(prev.ttm_rate, 0) - 1 as yoy_delta,
    t.ttm_rate / nullif(b.base_2019, 0) * 100 as index_2019
from ttm as t
left join ttm as prev
    on prev.level = t.level
    and prev.area = t.area
    and prev.offense = t.offense
    and prev.period = t.period - interval '1 year'
left join baseline_2019 as b
    on b.level = t.level
    and b.area = t.area
    and b.offense = t.offense
