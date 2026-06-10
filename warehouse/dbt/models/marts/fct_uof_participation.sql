-- Use-of-Force national participation, one row per year.
select
    year,
    participating_agencies,
    total_agencies,
    participation_percent
from {{ ref('stg_uof_participation') }}
