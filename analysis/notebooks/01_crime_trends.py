# ---
# jupyter:
#   jupytext:
#     formats: py:percent,ipynb
#     text_representation:
#       extension: .py
#       format_name: percent
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # OpenHydra — National crime trends
#
# Analysis over the DuckDB marts built by the dbt layer
# (`fct_offenses_monthly`, `fct_arrests`). Three questions:
#
# 1. **Did crime spike during the COVID era?** (offense rates, indexed to 2019)
# 2. **Are crimes being solved less often?** (clearance over time)
# 3. **Who gets arrested?** (national arrest demographics)
#
# The notebook pins its inputs: the data release (`EXPECTED_RELEASE`) and the
# observation window (`WINDOW`). Each query filters on the window, and the run
# stops if the warehouse holds another release. Charts, a CSV of the plotted
# values and a provenance file go to `../outputs/`.

# %%
# DuckDB 2: a query that becomes a Polars frame uses con.sql(...).pl(); the
# result of con.execute() has no .pl().
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import plotly.express as px
import plotly.io as pio
import polars as pl

pio.templates.default = "plotly_white"

HERE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
ROOT = HERE.parents[1]
DUCKDB = ROOT / "warehouse" / "openhydra.duckdb"
OUT = HERE.parent / "outputs"
OUT.mkdir(exist_ok=True)

# The release and the window that FINDINGS.md describes. Change them together
# with FINDINGS.md. Set OPENHYDRA_ANY_RELEASE=1 to explore another release.
EXPECTED_RELEASE = "20261123T130946Z"
WINDOW = ("2015-01-01", "2024-12-01")  # first and last month, inclusive
WINDOW_LABEL = f"{WINDOW[0][:4]}–{WINDOW[1][:4]}"

con = duckdb.connect(str(DUCKDB), read_only=True)
release = con.sql(
    "select release_id, extracted_at_min, extracted_at_max, window_from, window_to, reconstructed"
    " from meta_snapshot"
).fetchall()[0]
assert release is not None, "meta_snapshot is empty: build the warehouse with `make data`"
if release[0] != EXPECTED_RELEASE and not os.environ.get("OPENHYDRA_ANY_RELEASE"):
    raise SystemExit(
        f"The warehouse holds release {release[0]}, not {EXPECTED_RELEASE}. "
        "Update EXPECTED_RELEASE and FINDINGS.md, or set OPENHYDRA_ANY_RELEASE=1."
    )
print(f"Release {release[0]} (extracted {release[1]} to {release[2]}), window {WINDOW_LABEL}")

VALUES: list[dict[str, object]] = []  # every plotted point, for outputs/values.csv


def save(fig, name: str, frame: pl.DataFrame, x: str, y: str, series: str) -> None:
    """Write an interactive HTML always, a PNG when kaleido is available, and keep
    the plotted values for the CSV."""
    for row in frame.select([series, x, y]).iter_rows():
        VALUES.append({"figure": name, "series": row[0], "x": str(row[1]), "y": row[2]})
    fig.write_html(OUT / f"{name}.html", include_plotlyjs="cdn")
    try:
        fig.write_image(OUT / f"{name}.png", width=1000, height=560, scale=2)
        print(f"  saved {name}.png + .html")
    except Exception as exc:  # noqa: BLE001
        print(f"  saved {name}.html (PNG export skipped: {type(exc).__name__})")


# %% [markdown]
# ## 1. Crime through the COVID era (indexed to 2019)
#
# The index comes from the mart, so the dashboard and this notebook use one
# definition: the trailing-12-month (TTM) rate divided by the mean monthly rate
# of calendar 2019, times 100. December 2019 is 100. The TTM rate needs all 12
# calendar months, so the series starts in December of the first year.

# %%
off = (
    con.sql(
        """
        select period, offense, index_2019
        from fct_offenses_monthly
        where level = 'national'
          and offense in ('homicide','aggravated-assault','motor-vehicle-theft','property-crime','burglary')
          and period between ? and ?
          and index_2019 is not null
        order by offense, period
        """,
        params=list(WINDOW),
    )
    .pl()
)

fig1 = px.line(
    off.to_pandas(),
    x="period",
    y="index_2019",
    color="offense",
    labels={"index_2019": "TTM offense rate (December 2019 = 100)", "period": ""},
    title=f"U.S. crime relative to 2019, by offense (trailing 12 months, {WINDOW_LABEL})",
)
fig1.add_hline(y=100, line_dash="dot", line_color="gray")
fig1.add_vrect(
    x0="2020-03-01", x1="2021-12-31", fillcolor="red", opacity=0.07, line_width=0,
    annotation_text="COVID era", annotation_position="top left",
)
save(fig1, "01_covid_indexed", off, "period", "index_2019", "offense")

# Headline numbers
for offense_name in ("homicide", "motor-vehicle-theft"):
    pk = off.filter(pl.col("offense") == offense_name).sort("index_2019", descending=True).head(1)
    print(f"  {offense_name} peak vs 2019:", pk.select(["period", "index_2019"]).to_dicts())
    last = off.filter(pl.col("offense") == offense_name).sort("period").tail(1)
    print(f"  {offense_name} at window end:", last.select(["period", "index_2019"]).to_dicts())

# %% [markdown]
# ## 2. Clearance over time (are crimes being solved?)
#
# Annual clearance = cleared ÷ reported, both summed over the months of the year
# that report both counts (a ratio of sums). The chart keeps complete years only
# (12 such months). The FBI counts a clearance in the month it happens, which
# can be a later month than the offense, so this is not the share of the same
# year's offenses that were solved.

# %%
clr = (
    con.sql(
        """
        select date_part('year', period) as year, offense,
               sum(clearances_actual) / sum(offenses_actual) as clearance,
               count(*) as months
        from fct_offenses_monthly
        where level = 'national'
          and offense in ('homicide','aggravated-assault','robbery','burglary','motor-vehicle-theft')
          and period between ? and ?
          and clearances_actual is not null and offenses_actual is not null
        group by 1, 2
        having count(*) = 12
        order by offense, year
        """,
        params=list(WINDOW),
    )
    .pl()
)

fig2 = px.line(
    clr.to_pandas(),
    x="year",
    y="clearance",
    color="offense",
    markers=True,
    labels={"clearance": "Cleared ÷ reported (annual sums)", "year": ""},
    title=f"U.S. clearance by offense, complete years ({WINDOW_LABEL})",
)
fig2.update_yaxes(tickformat=".0%")
save(fig2, "02_clearance_ratio", clr, "year", "clearance", "offense")
for row in clr.filter(pl.col("year") == int(WINDOW[1][:4])).iter_rows(named=True):
    print(f"  clearance {row['year']} {row['offense']}: {row['clearance']:.1%}")

# %% [markdown]
# ## 3. National arrest demographics
#
# From `fct_arrests` (totals over the extract window). Race + sex composition,
# and the age profile of male vs female arrests. Each query selects one offense,
# `all` (every offense together): `fct_arrests` holds one set of rows per
# offense, so a query without an offense filter would add them up several times.

# %%
ARREST_OFFENSE = "all"
arrest_window = con.sql(
    "select min(window_from), max(window_to) from fct_arrests where offense = ?",
    params=[ARREST_OFFENSE],
).fetchall()[0]
ARREST_WINDOW = f"{arrest_window[0]} to {arrest_window[1]}"
# The arrest totals cover their extract window; it must be the notebook window.
assert (arrest_window[0], arrest_window[1]) == (
    f"{WINDOW[0][5:7]}-{WINDOW[0][:4]}",
    f"{WINDOW[1][5:7]}-{WINDOW[1][:4]}",
), f"arrest window {ARREST_WINDOW} differs from {WINDOW_LABEL}"
race = (
    con.sql(
        """
        select label as race, value as arrests
        from fct_arrests
        where level = 'national' and offense = ? and category = 'Arrestee Race' and value > 0
        order by arrests desc
        """,
        params=[ARREST_OFFENSE],
    )
    .pl()
)
# One row per race label for the chosen offense.
assert race["race"].is_unique().all(), "duplicate race labels: check the offense filter"
fig3 = px.bar(
    race.to_pandas(),
    x="arrests",
    y="race",
    orientation="h",
    labels={"arrests": "Arrests", "race": ""},
    title=f"National arrests by race, all offenses ({ARREST_WINDOW})",
)
fig3.update_yaxes(categoryorder="total ascending")
save(fig3, "03_arrests_by_race", race.with_columns(pl.lit("all").alias("offense")), "race", "arrests", "offense")

# %%
# Buckets mix single years (15–24) with 5-year bands, so divide each by its
# width to get a comparable "arrests per year of age". ("65 and over" is
# open-ended and dropped.)
AGE_WIDTH = {
    "13-14": 2, "15": 1, "16": 1, "17": 1, "18": 1, "19": 1, "20": 1, "21": 1,
    "22": 1, "23": 1, "24": 1, "25-29": 5, "30-34": 5, "35-39": 5, "40-44": 5,
    "45-49": 5, "50-54": 5, "55-59": 5, "60-64": 5,
}
AGE_ORDER = list(AGE_WIDTH)
age = (
    con.sql(
        """
        select
            label as age_band,
            case when category = 'Male Arrests By Age' then 'Male' else 'Female' end as sex,
            value as arrests
        from fct_arrests
        where level = 'national' and offense = ?
          and category in ('Male Arrests By Age','Female Arrests By Age')
        """,
        params=[ARREST_OFFENSE],
    )
    .pl()
    .filter(pl.col("age_band").is_in(AGE_ORDER))
    .with_columns(
        (pl.col("arrests") / pl.col("age_band").replace_strict(AGE_WIDTH, return_dtype=pl.Int32))
        .alias("per_year")
    )
)
fig4 = px.line(
    age.to_pandas(),
    x="age_band",
    y="per_year",
    color="sex",
    markers=True,
    category_orders={"age_band": AGE_ORDER},
    labels={"per_year": f"Arrests per year of age ({ARREST_WINDOW})", "age_band": "Age"},
    title="National arrests by age and sex (per year of age)",
)
assert not age.select(["age_band", "sex"]).is_duplicated().any(), "duplicate age rows"
save(fig4, "04_arrests_by_age", age, "age_band", "per_year", "sex")

# %% [markdown]
# ## Provenance
#
# `values.csv` holds every plotted point. `provenance.json` names the release,
# the window and the time of this run.

# %%
pl.DataFrame(VALUES, schema={"figure": pl.String, "series": pl.String, "x": pl.String, "y": pl.Float64}).write_csv(
    OUT / "values.csv"
)
(OUT / "provenance.json").write_text(
    json.dumps(
        {
            "release_id": release[0],
            "extracted_at_min": str(release[1]),
            "extracted_at_max": str(release[2]),
            "release_window": [release[3], release[4]],
            "reconstructed": bool(release[5]),
            "notebook_window": list(WINDOW),
            "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        },
        indent=2,
    )
    + "\n"
)
print("\nDone. Charts, values.csv and provenance.json in", OUT)
