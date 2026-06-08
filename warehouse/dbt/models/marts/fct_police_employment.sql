select
    level,
    area,
    section,
    metric,
    year,
    value
from {{ ref('stg_police_employment') }}
