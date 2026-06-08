select
    level,
    area,
    category,
    label,
    value
from {{ ref('stg_arrests') }}
