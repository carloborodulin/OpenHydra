-- Use-of-Force report items by year and quest category. Raw is already
-- aggregated; sum defensively against duplicate landed frames.
select
    year,
    category,
    label,
    sum(value) as value
from {{ ref('stg_uof_questions') }}
group by year, category, label
