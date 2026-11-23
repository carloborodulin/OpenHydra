-- Supplementary Homicide Report breakdowns by section and dimension.
-- The staging model test enforces one row per (level, area, category, label),
-- so a duplicate extract fails the build. No sum() can hide it here.
select
    level, area, category, label,
    value
from {{ ref('stg_shr') }}
