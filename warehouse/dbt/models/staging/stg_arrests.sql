-- One row per area, arrest code and breakdown label. `offense` is the canonical
-- arrest slug of `arrest_code`; `window_from`/`window_to` give the request window.
select
    level,
    area,
    offense,
    arrest_code,
    window_from,
    window_to,
    category,
    label,
    value
from {{ source('raw', 'arrests') }}
