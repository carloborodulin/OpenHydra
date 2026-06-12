-- One row per level/area/year with U.S. Census population, the denominator for
-- per-capita normalization of raw-count domains (arrests, property values).
select
    level,
    area,
    year,
    population
from {{ ref('stg_population') }}
