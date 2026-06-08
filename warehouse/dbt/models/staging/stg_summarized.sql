select
    level,
    area,
    offense,
    series,
    measure,
    period,
    value
from {{ source('raw', 'summarized') }}
