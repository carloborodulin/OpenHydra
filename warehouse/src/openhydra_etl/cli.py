"""`oh-etl` command-line interface."""

from __future__ import annotations

import sys
from typing import Annotated

import typer
from cdeclient import STATES, CdeClient, CdeError

from .extract import ALL_ARREST_OFFENSES, ALL_OFFENSES, Extractor

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
    help="OpenHydra ETL — pull FBI CDE data into the warehouse (data/raw/*.parquet).",
)


@app.callback()
def _root() -> None:
    """OpenHydra ETL commands."""  # keeps `pull` a named subcommand (room for load/build).


def _split(csv: str) -> list[str]:
    return [x.strip() for x in csv.split(",") if x.strip()]


@app.command()
def pull(
    from_: Annotated[str, typer.Option("--from", help="Start month, MM-YYYY.")] = "01-2015",
    to: Annotated[str, typer.Option("--to", help="End month, MM-YYYY.")] = "12-2024",
    states: Annotated[
        str, typer.Option("--states", help="Comma states, or 'all'. Blank = national only.")
    ] = "",
    offenses: Annotated[
        str, typer.Option("--offenses", help="Comma offense slugs. Blank = all 10.")
    ] = "",
    arrest_offenses: Annotated[
        str,
        typer.Option(
            "--arrest-offenses",
            help="Comma arrest offense slugs, or 'all' for all 48. Blank = same as --offenses.",
        ),
    ] = "",
    domains: Annotated[
        str, typer.Option("--domains", help="Which domains to pull.")
    ] = "summarized,agencies,arrests,pe",
) -> None:
    """Pull data and land tidy Parquet under data/raw/."""
    st = list(STATES) if states.strip().lower() == "all" else [s.upper() for s in _split(states)]
    offs = [o.lower() for o in _split(offenses)] or ALL_OFFENSES
    if arrest_offenses.strip().lower() == "all":
        # Full 48-code taxonomy, plus the summarized offenses so the aggregate
        # slugs (violent-crime/property-crime) stay available for overview panels.
        aoffs = list(dict.fromkeys([*offs, *ALL_ARREST_OFFENSES]))
    else:
        aoffs = [a.lower() for a in _split(arrest_offenses)] or offs
    doms = [d.lower() for d in _split(domains)]

    # Generous retries + a longer read timeout: a bulk pull makes many calls and
    # the gateway throws intermittent 503 spells and slow responses (notably the
    # modeled NIBRS estimations); ride through them rather than aborting mid-run.
    with CdeClient(timeout=60.0, max_attempts=8, base_wait=1.0, max_wait=30.0) as client:
        ex = Extractor(client)
        if "summarized" in doms:
            f = ex.pull_summarized(offs, st, from_, to)
            typer.echo(
                f"summarized -> {f.height} rows ({len(offs)} offenses, {len(st)} states + national)"
            )
        if "agencies" in doms:
            if st:
                f = ex.pull_agencies(st)
                typer.echo(f"agencies   -> {f.height} rows ({len(st)} states)")
            else:
                typer.echo("agencies   -> skipped (pass --states; agencies are per-state)")
        if "arrests" in doms:
            f = ex.pull_arrests(st, aoffs, from_, to)
            n = len(aoffs)
            typer.echo(f"arrests    -> {f.height} rows ({n} offenses, {len(st)} states + national)")
        if "hate-crime" in doms:
            f = ex.pull_hate_crime(st, from_, to)
            typer.echo(f"hate-crime -> {f.height} rows ({len(st)} states + national)")
        if "shr" in doms:
            f = ex.pull_shr(st, from_, to)
            typer.echo(f"shr        -> {f.height} rows ({len(st)} states + national)")
        if "property" in doms:
            f = ex.pull_property(st, from_, to)
            typer.echo(f"property   -> {f.height} rows ({len(st)} states + national)")
        if "nibrs" in doms:
            f = ex.pull_nibrs(st, from_, to)
            typer.echo(f"nibrs      -> {f.height} rows ({len(st)} states + national)")
        if "lesdc" in doms:
            f = ex.pull_lesdc()  # national-only, year-keyed (ignores --states/--from/--to)
            typer.echo(f"lesdc      -> {f.height} rows")
        if "uof" in doms:
            pf, qf = ex.pull_uof()  # national-only, year-keyed
            typer.echo(f"uof        -> {pf.height} participation, {qf.height} question rows")
        if "nibrs-estimation" in doms:
            f = ex.pull_nibrs_estimation()  # national + regions, curated offenses
            typer.echo(f"nibrs-est  -> {f.height} rows")
        if "pe" in doms:
            f = ex.pull_pe(st, from_, to)
            typer.echo(f"pe         -> {f.height} rows")


def main() -> None:
    try:
        app()
    except CdeError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
