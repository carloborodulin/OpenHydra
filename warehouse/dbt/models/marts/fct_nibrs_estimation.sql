-- NIBRS estimated counts by geography (national or region), offense and dimension.
-- The staging model test enforces one row per (level, area, offense, category, label),
-- so a duplicate extract fails the build. No sum() can hide it here.
select
    level, area, offense, category, label,
    value,
    -- The FBI interval of the estimate (null in releases before 2026-11).
    lower,
    upper
from {{ ref('stg_nibrs_estimation') }}
