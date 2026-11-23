-- Hate crime incident and offense breakdowns by dimension.
-- The staging model test enforces one row per (level, area, category, label),
-- so a duplicate extract fails the build. No sum() can hide it here.
select
    level, area, category, label,
    value
from {{ ref('stg_hate_crime') }}
