select
    level,
    area,
    category,
    label,
    value
from {{ source('raw', 'hate_crime') }}
