-- Expanded property (supplemental) breakdowns by offense, year and dimension.
-- A null year means a total over the whole extract window (the older seed).
-- The staging model test enforces one row per (level, area, offense, year, category, label),
-- so a duplicate extract fails the build. No sum() can hide it here.
select
    level, area, offense, year, category, label,
    value
from {{ ref('stg_property') }}
