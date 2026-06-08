select
    level,
    area,
    section,
    metric,
    year,
    value
from {{ source('raw', 'pe') }}
