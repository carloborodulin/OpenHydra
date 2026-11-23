-- One row per file of the data release: when it was extracted, its window and
-- its row count. A view uses it to state the coverage of its own data (for
-- example LESDC covers 2022 to 2023 only).
select
    je.key as domain,
    cast(je.value ->> '$.extracted_at' as timestamp) as extracted_at,
    je.value -> '$.window' ->> '$.from' as window_from,
    je.value -> '$.window' ->> '$.to' as window_to,
    cast(je.value ->> '$.rows' as bigint) as row_count,
    je.value ->> '$.status' as status
from read_text('../../data/raw/_manifest.json') as manifest,
    json_each(cast(manifest.content as json) -> '$.domains') as je
