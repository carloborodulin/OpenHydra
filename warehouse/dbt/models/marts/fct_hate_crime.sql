-- Hate crime incident/offense breakdowns by dimension. The raw feed is already
-- aggregated per area, so sum defensively in case an area appears in more than
-- one landed frame.
select
    level,
    area,
    category,
    label,
    sum(value) as value
from {{ ref('stg_hate_crime') }}
group by level, area, category, label
