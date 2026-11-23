select
    level,
    area,
    offense,
    category,
    label,
    value,
    lower,
    upper
from {{ source('raw', 'nibrs_estimation') }}
