"""`oh-etl` command-line interface."""

from __future__ import annotations

import sys
from typing import Annotated

import typer
from cdeclient import STATES, CdeClient, CdeError

from .extract import ALL_OFFENSES, Extractor

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
    from_: Annotated[str, typer.Option("--from", help="Start month, MM-YYYY.")] = "01-2020",
    to: Annotated[str, typer.Option("--to", help="End month, MM-YYYY.")] = "12-2022",
    states: Annotated[
        str, typer.Option("--states", help="Comma states, or 'all'. Blank = national only.")
    ] = "",
    offenses: Annotated[
        str, typer.Option("--offenses", help="Comma offense slugs. Blank = all 10.")
    ] = "",
    domains: Annotated[
        str, typer.Option("--domains", help="Which domains to pull.")
    ] = "summarized,agencies,arrests,pe",
) -> None:
    """Pull data and land tidy Parquet under data/raw/."""
    st = list(STATES) if states.strip().lower() == "all" else [s.upper() for s in _split(states)]
    offs = [o.lower() for o in _split(offenses)] or ALL_OFFENSES
    doms = [d.lower() for d in _split(domains)]

    # Generous retries: a bulk pull makes many calls and the gateway throws
    # intermittent 503 spells; ride through them rather than aborting mid-run.
    with CdeClient(max_attempts=8, base_wait=1.0, max_wait=30.0) as client:
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
            f = ex.pull_arrests(st, from_, to)
            typer.echo(f"arrests    -> {f.height} rows")
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
