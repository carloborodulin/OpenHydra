-- LESDC (LE suicide data collection) by year, chart type, S/AS section, and
-- label. National only; raw is already aggregated, sum defensively.
select
    year,
    chart_type,
    section,
    label,
    sum(value) as value
from {{ ref('stg_lesdc') }}
group by year, chart_type, section, label
