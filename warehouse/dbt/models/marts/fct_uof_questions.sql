-- Use-of-force report items by year and question category.
-- The staging model test enforces one row per (year, category, label),
-- so a duplicate extract fails the build. No sum() can hide it here.
select
    year, category, label,
    value
from {{ ref('stg_uof_questions') }}
