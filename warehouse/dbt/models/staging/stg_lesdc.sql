select
    year,
    chart_type,
    section,
    label,
    value
from {{ source('raw', 'lesdc') }}
