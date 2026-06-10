-- Supplementary Homicide Report breakdowns by section_dimension. The raw feed is
-- already aggregated per area; sum defensively against duplicate landed frames.
select
    level,
    area,
    category,
    label,
    sum(value) as value
from {{ ref('stg_shr') }}
group by level, area, category, label
