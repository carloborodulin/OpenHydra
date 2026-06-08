# analysis — OpenHydra notebooks

Data-science layer: **Polars + Plotly** analyses over the **DuckDB marts** built by
the [warehouse](../warehouse) dbt layer. Findings writeup: [FINDINGS.md](FINDINGS.md).

```
warehouse/openhydra.duckdb (marts) ──▶ notebooks (Polars + Plotly) ──▶ outputs/*.png
```

## Run

```bash
cd analysis
uv sync
uv run python notebooks/01_crime_trends.py     # computes + writes charts to outputs/
```

Requires the warehouse to exist first (`warehouse/openhydra.duckdb`) — build it via
the [warehouse](../warehouse) ELT + dbt steps.

## Notebooks

Authored in **jupytext percent format** (`.py` is the source of truth) and paired to
`.ipynb`. To open interactively or regenerate the notebook:

```bash
uv run jupyter lab                                   # explore
uv run jupytext --to notebook notebooks/01_crime_trends.py   # regenerate .ipynb
```

| notebook | what |
|---|---|
| `01_crime_trends.py` | COVID-era offense trends (indexed), clearance ratios, arrest demographics |

Charts are written as both PNG (committed, for the writeup) and interactive HTML.
