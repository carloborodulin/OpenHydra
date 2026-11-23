-- LESDC (law enforcement suicide data collection) by year, chart type, section and label. National only.
-- The staging model test enforces one row per (year, chart_type, section, label),
-- so a duplicate extract fails the build. No sum() can hide it here.
select
    year, chart_type, section, label,
    value
from {{ ref('stg_lesdc') }}
