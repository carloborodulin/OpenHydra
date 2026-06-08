-- One row per ORI (deduplicated across pulls), with NIBRS adoption year.
select
    ori,
    any_value(agency_name) as agency_name,
    any_value(agency_type) as agency_type,
    any_value(county) as county,
    any_value(state_abbr) as state_abbr,
    any_value(state_name) as state_name,
    any_value(latitude) as latitude,
    any_value(longitude) as longitude,
    bool_or(is_nibrs) as is_nibrs,
    min(nibrs_start_date) as nibrs_start_date,
    year(min(nibrs_start_date)) as nibrs_start_year
from {{ ref('stg_agencies') }}
group by ori
