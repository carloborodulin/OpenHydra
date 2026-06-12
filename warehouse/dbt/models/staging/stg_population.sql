-- Census population estimates seed. `US` is the national total; everything else is
-- a state/DC USPS code matching the marts' `area`. Derive `level` to match the
-- national/state convention used across the fact tables.
select
    case when area = 'US' then 'national' else 'state' end as level,
    area,
    cast(year as integer) as year,
    cast(population as bigint) as population
from {{ source('seeds', 'population') }}
