"""Fetch U.S. Census population estimates (state + national, 2015-2024) into the
committed seed CSV at data/seeds/population.csv.

Run once to (re)generate the seed; the warehouse build reads the committed CSV, so
network is only needed when refreshing. Provenance — Census Population Estimates
Program (PEP):
  2015-2019: Vintage 2019 national/state totals (nst-est2019-alldata.csv)
  2020-2024: Vintage 2024 state totals (NST-EST2024-ALLDATA.csv)

Usage: uv run python scripts/fetch_population.py
"""

from __future__ import annotations

import io
import urllib.request
from pathlib import Path

import polars as pl

V2019 = (
    "https://www2.census.gov/programs-surveys/popest/datasets/"
    "2010-2019/national/totals/nst-est2019-alldata.csv"
)
V2024 = (
    "https://www2.census.gov/programs-surveys/popest/datasets/"
    "2020-2024/state/totals/NST-EST2024-ALLDATA.csv"
)

# Census NAME -> USPS area code used by the marts (50 states + DC + national).
NAME_TO_AREA = {
    "United States": "US",
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
    "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
    "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}

OUT = Path(__file__).resolve().parents[2] / "data" / "seeds" / "population.csv"


def _read(url: str) -> pl.DataFrame:
    with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 (trusted Census host)
        return pl.read_csv(io.BytesIO(r.read()))


def main() -> None:
    rows: list[dict[str, int | str]] = []
    for df, years in ((_read(V2019), range(2015, 2020)), (_read(V2024), range(2020, 2025))):
        # SUMLEV 010 = national, 040 = state.
        sub = df.filter(pl.col("SUMLEV").cast(pl.Int64, strict=False).is_in([10, 40]))
        for rec in sub.iter_rows(named=True):
            area = NAME_TO_AREA.get(rec["NAME"])
            if not area:
                continue
            for y in years:
                val = rec.get(f"POPESTIMATE{y}")
                if val is not None:
                    rows.append({"area": area, "year": y, "population": int(val)})

    out = pl.DataFrame(rows).sort(["area", "year"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.write_csv(OUT)
    print(f"wrote {len(out)} rows ({out['area'].n_unique()} areas) -> {OUT}")


if __name__ == "__main__":
    main()
