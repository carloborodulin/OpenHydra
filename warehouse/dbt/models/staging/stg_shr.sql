select
    level,
    area,
    category,
    label,
    value
from {{ source('raw', 'shr') }}
