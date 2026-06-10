select
    level,
    area,
    offense,
    category,
    label,
    value
from {{ source('raw', 'nibrs_estimation') }}
