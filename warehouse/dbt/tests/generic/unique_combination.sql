-- Fails when two rows share the same values in all of the given columns.
-- Use it to state the grain of a model, for example (level, area, period).
{% test unique_combination(model, columns) %}
select {{ columns | join(', ') }}, count(*) as row_count
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}
