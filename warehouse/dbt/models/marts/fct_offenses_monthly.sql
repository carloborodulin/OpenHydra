-- One row per level/area/offense/month, pivoting the long series/measure rows
-- into offense & clearance columns, plus a derived clearance ratio and a set of
-- trailing-12-month trend metrics (TTM rate, YoY delta, index vs 2019 baseline).
with s as (
    select * from {{ ref('stg_summarized') }}
),

pivoted as (
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
),

-- Trailing-12-month average rate de-seasonalizes the noisy monthly series.
ttm as (
    select
        *,
        avg(offenses_rate) over (
            partition by level, area, offense
            order by period
            rows between 11 preceding and current row
        ) as ttm_rate
    from pivoted
),

-- Per-series mean 2019 rate, used to index every period to its 2019 baseline.
baseline_2019 as (
    select level, area, offense, avg(offenses_rate) as base_2019
    from pivoted
    where year(period) = 2019
    group by level, area, offense
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
    t.ttm_rate,
    -- YoY change in the trailing-12-month rate vs the same month one year prior.
    -- Date-join (not lag(12)) so it stays correct if any month is missing.
    t.ttm_rate / nullif(prev.ttm_rate, 0) - 1 as yoy_delta,
    -- Index the de-seasonalized (trailing-12-month) rate to the 2019 mean: 2019 = 100,
    -- >100 means elevated vs pre-pandemic baseline. Using ttm_rate (not the raw monthly
    -- rate) keeps the index robust to monthly outliers (e.g. a Dec reporting spike).
    t.ttm_rate / nullif(b.base_2019, 0) * 100 as index_2019
from ttm t
left join ttm prev
    on prev.level = t.level
   and prev.area = t.area
   and prev.offense = t.offense
   and prev.period = t.period - interval '1 year'
left join baseline_2019 b
    on b.level = t.level
   and b.area = t.area
   and b.offense = t.offense
