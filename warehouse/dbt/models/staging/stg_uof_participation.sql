select
    year,
    participating_agencies,
    total_agencies,
    participation_percent
from {{ source('raw', 'uof_participation') }}
