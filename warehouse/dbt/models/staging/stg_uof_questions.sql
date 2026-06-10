select
    year,
    category,
    label,
    value
from {{ source('raw', 'uof_questions') }}
