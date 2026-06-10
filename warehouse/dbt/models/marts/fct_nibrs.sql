-- NIBRS incident breakdowns by offense and section_dimension. Raw is already
-- aggregated per area; sum defensively against duplicate landed frames.
select
    level,
    area,
    offense,
    category,
    label,
    sum(value) as value
from {{ ref('stg_nibrs') }}
group by level, area, offense, category, label
