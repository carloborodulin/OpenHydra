-- NIBRS estimated counts by geography (national/region), offense, and
-- section_dimension. Raw is already aggregated; sum defensively.
select
    level,
    area,
    offense,
    category,
    label,
    sum(value) as value
from {{ ref('stg_nibrs_estimation') }}
group by level, area, offense, category, label
