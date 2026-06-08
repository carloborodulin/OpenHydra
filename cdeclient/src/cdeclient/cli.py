"""`cde` command-line interface."""

from __future__ import annotations

import json
import sys
from typing import Annotated, Any

import typer

from .client import CdeClient, CdeError
from .constants import ArrestType, Offense

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,  # we handle CdeError cleanly in main()
    help="Query the FBI Crime Data Explorer (CDE) API.",
)
summarized_app = typer.Typer(no_args_is_help=True, help="Monthly offense & clearance series.")
arrests_app = typer.Typer(no_args_is_help=True, help="Arrest totals / counts.")
pe_app = typer.Typer(no_args_is_help=True, help="Police employment (yearly).")
app.add_typer(summarized_app, name="summarized")
app.add_typer(arrests_app, name="arrests")
app.add_typer(pe_app, name="pe")

# Reusable option/argument definitions (module-level singletons).
MonthFrom = Annotated[str, typer.Option("--from", help="Start month, MM-YYYY.")]
MonthTo = Annotated[str, typer.Option("--to", help="End month, MM-YYYY.")]
YearFrom = Annotated[str, typer.Option("--from", help="Start year, YYYY.")]
YearTo = Annotated[str, typer.Option("--to", help="End year, YYYY.")]
TypeOpt = Annotated[ArrestType, typer.Option("--type", help="totals or counts.")]
OffenseArg = Annotated[str, typer.Argument(help="Offense slug, or 'all'.")]


def _emit(obj: Any) -> None:
    if hasattr(obj, "model_dump"):
        obj = obj.model_dump()
    typer.echo(json.dumps(obj, indent=2, default=str))


@app.command()
def agencies(state: str) -> None:
    """List agencies for a state (e.g. NY), grouped by county."""
    with CdeClient() as c:
        result = c.agencies_by_state(state)
    _emit({county: [a.model_dump() for a in ags] for county, ags in result.items()})


@summarized_app.command("national")
def summarized_national(offense: Offense, from_: MonthFrom, to: MonthTo) -> None:
    with CdeClient() as c:
        _emit(c.summarized_national(offense, from_, to))


@summarized_app.command("state")
def summarized_state(state: str, offense: Offense, from_: MonthFrom, to: MonthTo) -> None:
    with CdeClient() as c:
        _emit(c.summarized_state(state, offense, from_, to))


@summarized_app.command("agency")
def summarized_agency(ori: str, offense: Offense, from_: MonthFrom, to: MonthTo) -> None:
    with CdeClient() as c:
        _emit(c.summarized_agency(ori, offense, from_, to))


@arrests_app.command("national")
def arrests_national(
    from_: MonthFrom,
    to: MonthTo,
    offense: OffenseArg = "all",
    arrest_type: TypeOpt = ArrestType.TOTALS,
) -> None:
    with CdeClient() as c:
        _emit(c.arrests_national(offense, arrest_type=arrest_type, from_=from_, to=to))


@arrests_app.command("state")
def arrests_state(
    state: str,
    from_: MonthFrom,
    to: MonthTo,
    offense: OffenseArg = "all",
    arrest_type: TypeOpt = ArrestType.TOTALS,
) -> None:
    with CdeClient() as c:
        _emit(c.arrests_state(state, offense, arrest_type=arrest_type, from_=from_, to=to))


@pe_app.command("national")
def pe_national(from_: YearFrom, to: YearTo) -> None:
    with CdeClient() as c:
        _emit(c.police_employment_national(from_, to))


@pe_app.command("state")
def pe_state(state: str, from_: YearFrom, to: YearTo) -> None:
    with CdeClient() as c:
        _emit(c.police_employment_state(state, from_, to))


def main() -> None:
    try:
        app()
    except CdeError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
