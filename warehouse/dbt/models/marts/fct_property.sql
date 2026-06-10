-- Expanded property (supplemental) value/count breakdowns by offense and
-- dimension. Raw is already aggregated per area; sum defensively.
select
    level,
    area,
    offense,
    category,
    label,
    sum(value) as value
from {{ ref('stg_property') }}
group by level, area, offense, category, label
