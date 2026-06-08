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
# # OpenHydra — National crime trends (2017–2023)
#
# Analysis over the DuckDB marts built by the dbt layer
# (`fct_offenses_monthly`, `fct_arrests`). Three questions:
#
# 1. **Did crime spike during the COVID era?** (offense rates, indexed to 2019)
# 2. **Are crimes being solved less often?** (clearance ratios over time)
# 3. **Who gets arrested?** (national arrest demographics)
#
# Charts are written to `../outputs/`.

# %%
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

con = duckdb.connect(str(DUCKDB), read_only=True)


def save(fig, name: str) -> None:
    """Write an interactive HTML always, and a PNG when kaleido is available."""
    fig.write_html(OUT / f"{name}.html", include_plotlyjs="cdn")
    try:
        fig.write_image(OUT / f"{name}.png", width=1000, height=560, scale=2)
        print(f"  saved {name}.png + .html")
    except Exception as exc:  # noqa: BLE001
        print(f"  saved {name}.html (PNG export skipped: {type(exc).__name__})")


# %% [markdown]
# ## 1. Crime through the COVID era (indexed to each offense's 2019 average)
#
# Indexing to the 2019 mean (=100) puts offenses with very different absolute
# rates on one comparable axis, so the relative size of the 2020+ shift is clear.

# %%
off = (
    con.execute(
        """
        select period, offense, offenses_rate
        from fct_offenses_monthly
        where level = 'national'
          and offense in ('homicide','aggravated-assault','motor-vehicle-theft','property-crime','burglary')
          and offenses_rate is not null
        order by offense, period
        """
    )
    .pl()
    # 12-month trailing average removes the strong seasonal (December) spikes.
    .with_columns(
        pl.col("offenses_rate")
        .rolling_mean(window_size=12, min_samples=6)
        .over("offense")
        .alias("smoothed")
    )
    .drop_nulls("smoothed")
)

baseline = (
    off.filter(pl.col("period").dt.year() == 2019)
    .group_by("offense")
    .agg(pl.col("smoothed").mean().alias("base_2019"))
)
indexed = off.join(baseline, on="offense").with_columns(
    (pl.col("smoothed") / pl.col("base_2019") * 100).alias("index_2019")
)

fig1 = px.line(
    indexed.to_pandas(),
    x="period",
    y="index_2019",
    color="offense",
    labels={"index_2019": "Offense rate, 12-mo avg (2019 = 100)", "period": ""},
    title="U.S. crime relative to 2019, by offense (12-month rolling, indexed)",
)
fig1.add_hline(y=100, line_dash="dot", line_color="gray")
fig1.add_vrect(
    x0="2020-03-01", x1="2021-12-31", fillcolor="red", opacity=0.07, line_width=0,
    annotation_text="COVID era", annotation_position="top left",
)
save(fig1, "01_covid_indexed")

# Headline numbers
for offense_name in ("homicide", "motor-vehicle-theft"):
    pk = indexed.filter(pl.col("offense") == offense_name).sort("index_2019", descending=True).head(1)
    print(f"  {offense_name} peak vs 2019:", pk.select(["period", "index_2019"]).to_dicts())

# %% [markdown]
# ## 2. Clearance ratios over time (are crimes being solved?)
#
# `clearance_ratio` = cleared ÷ reported (annual mean of the monthly marts).

# %%
clr = (
    con.execute(
        """
        select date_part('year', period) as year, offense, avg(clearance_ratio) as clearance
        from fct_offenses_monthly
        where level = 'national'
          and offense in ('homicide','aggravated-assault','robbery','burglary','motor-vehicle-theft')
          and clearance_ratio is not null
        group by 1, 2
        order by offense, year
        """
    )
    .pl()
)

fig2 = px.line(
    clr.to_pandas(),
    x="year",
    y="clearance",
    color="offense",
    markers=True,
    labels={"clearance": "Clearance ratio (cleared ÷ reported)", "year": ""},
    title="U.S. clearance ratios by offense (annual mean)",
)
fig2.update_yaxes(tickformat=".0%")
save(fig2, "02_clearance_ratio")

# %% [markdown]
# ## 3. National arrest demographics
#
# From `fct_arrests` (aggregated totals). Race + sex composition, and the
# age profile of male vs female arrests.

# %%
race = (
    con.execute(
        """
        select label as race, value as arrests
        from fct_arrests
        where level = 'national' and category = 'Arrestee Race' and value > 0
        order by arrests desc
        """
    )
    .pl()
)
fig3 = px.bar(
    race.to_pandas(),
    x="arrests",
    y="race",
    orientation="h",
    labels={"arrests": "Arrests", "race": ""},
    title="National arrests by race",
)
fig3.update_yaxes(categoryorder="total ascending")
save(fig3, "03_arrests_by_race")

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
    con.execute(
        """
        select
            label as age_band,
            case when category = 'Male Arrests By Age' then 'Male' else 'Female' end as sex,
            value as arrests
        from fct_arrests
        where level = 'national'
          and category in ('Male Arrests By Age','Female Arrests By Age')
        """
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
    labels={"per_year": "Arrests per year of age (2017–2023)", "age_band": "Age"},
    title="National arrests by age and sex (per year of age)",
)
save(fig4, "04_arrests_by_age")

print("\nDone. Charts in", OUT)
