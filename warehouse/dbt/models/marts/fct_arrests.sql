-- Arrest demographic breakdowns per offense.
--
-- The rows from the API keep their own arrest code (is_derived = false). Code
-- "all" is every offense together.
--
-- The CDE API has no code for violent crime or property crime. This model adds
-- them as the sum of their four Part I offenses (is_derived = true). Arrest
-- counts add across offense codes, because the UCR counts each arrest under one
-- offense. A rollup row exists only when all four parts exist for that area.
with base as (
    select
        level, area, offense, arrest_code, window_from, window_to,
        category, label, value,
        false as is_derived
    from {{ ref('stg_arrests') }}
),

rollup_parts as (
    select * from (values
        ('violent-crime', 'homicide'),
        ('violent-crime', 'rape'),
        ('violent-crime', 'robbery'),
        ('violent-crime', 'aggravated-assault'),
        ('property-crime', 'burglary'),
        ('property-crime', 'larceny'),
        ('property-crime', 'motor-vehicle-theft'),
        ('property-crime', 'arson')
    ) as t(rollup, part)
),

complete_areas as (
    select b.level, b.area, p.rollup
    from base b
    join rollup_parts p on p.part = b.offense
    group by b.level, b.area, p.rollup
    having count(distinct b.offense) = 4
),

derived as (
    select
        b.level,
        b.area,
        p.rollup as offense,
        cast(null as varchar) as arrest_code,
        min(b.window_from) as window_from,
        max(b.window_to) as window_to,
        b.category,
        b.label,
        sum(b.value) as value,
        true as is_derived
    from base b
    join rollup_parts p on p.part = b.offense
    join complete_areas c on c.level = b.level and c.area = b.area and c.rollup = p.rollup
    group by b.level, b.area, p.rollup, b.category, b.label
)

select * from base
union all
select * from derived
