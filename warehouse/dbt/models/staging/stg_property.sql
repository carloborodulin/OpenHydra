select
    level,
    area,
    offense,
    year,
    category,
    label,
    value
from {{ source('raw', 'property') }}
