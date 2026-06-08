select
    ori,
    agency_name,
    agency_type,
    county,
    state_abbr,
    state_name,
    latitude,
    longitude,
    is_nibrs,
    try_cast(nibrs_start_date as date) as nibrs_start_date
from {{ source('raw', 'agencies') }}
