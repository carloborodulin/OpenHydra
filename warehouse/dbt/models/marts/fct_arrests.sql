select
    level,
    area,
    offense,
    category,
    label,
    value
from {{ ref('stg_arrests') }}
