-- One row that describes the data release: its ID, the extraction dates, the
-- main window and the source. It comes from deploy/seed/_manifest.json, which
-- `make data` and the image copy to data/raw/. The API and the dashboard show it.
select
    release_id,
    cast(promoted_at as timestamp) as promoted_at,
    cast(extracted_at_min as timestamp) as extracted_at_min,
    cast(extracted_at_max as timestamp) as extracted_at_max,
    "window"."from" as window_from,
    "window"."to" as window_to,
    source,
    reconstructed
from read_json_auto('../../data/raw/_manifest.json')
