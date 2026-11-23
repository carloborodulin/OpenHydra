"""`oh-etl` command line.

oh-etl pull      Extract data into a staging directory (one run).
oh-etl promote   Make a staging run the next release in deploy/seed/.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import cdeclient
import typer
from cdeclient import BULK, STATES, CdeClient, CdeError
from cdeclient.dates import parse_window

from .config import RELEASE_DIR, STAGING_DIR
from .extract import (
    ALL_ARREST_OFFENSES,
    ALL_OFFENSES,
    DEFAULT_ARREST_OFFENSES,
    DomainFailed,
    Extractor,
)
from .snapshot import DOMAIN_FILES, PromoteError, RunLog, promote

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="OpenHydra ETL: CDE API -> staging Parquet -> a promoted release in deploy/seed/.",
)

# Every domain the dbt project reads. dbt needs all of them, so a first pull
# uses the default "all".
DOMAINS: tuple[str, ...] = tuple(DOMAIN_FILES)


def _split(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def _states(value: str) -> list[str]:
    if value.strip().lower() == "all":
        return list(STATES)
    # dict.fromkeys drops a repeated state, so no partition is pulled twice.
    states = list(dict.fromkeys(s.upper() for s in _split(value)))
    unknown = [s for s in states if s not in STATES]
    if unknown:
        raise typer.BadParameter(f"unknown states: {', '.join(unknown)}", param_hint="--states")
    return states


@app.callback()
def _root() -> None:
    """OpenHydra ETL."""


@app.command()
def pull(
    from_: Annotated[
        str, typer.Option("--from", help="Start month, MM-YYYY or YYYY-MM.")
    ] = "01-2015",
    to: Annotated[str, typer.Option("--to", help="End month, MM-YYYY or YYYY-MM.")] = "12-2024",
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
            help=(
                "Comma arrest offense slugs, or 'all' for all 48 codes. "
                "Blank = the all-offense total and the 8 Part I offenses."
            ),
        ),
    ] = "",
    domains: Annotated[
        str,
        typer.Option("--domains", help=f"Comma domains, or 'all'. Choices: {', '.join(DOMAINS)}."),
    ] = "all",
    out: Annotated[
        Path | None,
        typer.Option(
            "--out",
            help="Staging directory. A directory with a run manifest resumes that run. "
            "Default: data/staging/<run id>.",
        ),
    ] = None,
    per_hour: Annotated[
        float,
        typer.Option(
            "--per-hour",
            help="Maximum upstream requests per hour (0 = no limit). The default keeps "
            "about 30% of a 1,000 per hour key free for the live site.",
        ),
    ] = 700.0,
) -> None:
    """Pull data into a staging directory and record each request in its manifest."""
    try:
        window = parse_window(from_, to)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--from/--to") from None
    st = _states(states)
    offs = [o.lower() for o in _split(offenses)] or ALL_OFFENSES
    if arrest_offenses.strip().lower() == "all":
        aoffs = ALL_ARREST_OFFENSES  # the full 48-code taxonomy
    else:
        # The Part I codes let dbt build the violent/property rollups.
        aoffs = [a.lower() for a in _split(arrest_offenses)] or DEFAULT_ARREST_OFFENSES
    doms = (
        list(DOMAINS)
        if domains.strip().lower() == "all"
        else list(dict.fromkeys(d.lower() for d in _split(domains)))
    )
    unknown = [d for d in doms if d not in DOMAINS]
    if unknown:
        raise typer.BadParameter(f"unknown domains: {', '.join(unknown)}", param_hint="--domains")
    if "agencies" in doms and not st:
        raise typer.BadParameter("agencies are per state: pass --states", param_hint="--states")

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = out or STAGING_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        run = RunLog.load_or_new(
            out_dir,
            run_id=run_id,
            window={"from": window[0], "to": window[1]},
            states=st,
            client_version=cdeclient.__version__,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--out") from None
    typer.echo(f"run {run.run_id} -> {out_dir}")

    failed: list[str] = []
    with CdeClient(policy=BULK) as client:
        ex = Extractor(client, out_dir, run=run, per_hour=per_hour)
        for dom in doms:
            if run.domains.get(dom, {}).get("status") == "ok":
                typer.echo(f"{dom:<17} already complete in this run")
                continue
            run.start(dom)
            try:
                partial = _pull_domain(ex, dom, st, offs, aoffs, window)
            except DomainFailed as exc:
                run.fail(dom, str(exc))
                failed.append(dom)
                typer.secho(f"{dom:<17} FAILED: {exc}", fg=typer.colors.RED, err=True)
                continue
            files = [out_dir / f"{name}.parquet" for name in DOMAIN_FILES[dom]]
            run.finish(dom, files, partial=partial)
            facts = run.domains[dom]["files"]
            rows = ", ".join(f"{p.stem} {facts[p.stem]['rows']}" for p in files)
            typer.echo(f"{dom:<17} {'partial' if partial else 'ok':<8} {rows}")
    typer.echo(f"{ex.requests} upstream requests. Manifest: {out_dir / '_manifest.json'}")
    if failed:
        typer.secho(
            f"Failed domains: {', '.join(failed)}. Rerun with --out {out_dir} to resume.",
            fg=typer.colors.YELLOW,
            err=True,
        )
        raise typer.Exit(code=2)


def _pull_domain(
    ex: Extractor,
    dom: str,
    st: list[str],
    offs: list[str],
    aoffs: list[str],
    window: tuple[str, str],
) -> bool:
    """Pull one domain. Return True when the result is partial."""
    from_, to = window
    if dom == "summarized":
        ex.pull_summarized(offs, st, from_, to)
    elif dom == "agencies":
        ex.pull_agencies(st)
    elif dom == "arrests":
        ex.pull_arrests(st, aoffs, from_, to)
    elif dom == "pe":
        ex.pull_pe(st, from_, to)
    elif dom == "hate-crime":
        ex.pull_hate_crime(st, from_, to)
    elif dom == "shr":
        ex.pull_shr(st, from_, to)
    elif dom == "property":
        ex.pull_property(st, from_, to)
    elif dom == "nibrs":
        ex.pull_nibrs(st, from_, to)
    elif dom == "lesdc":
        ex.pull_lesdc()  # national-only, year-keyed
    elif dom == "uof":
        ex.pull_uof()  # national-only, year-keyed
    elif dom == "nibrs-estimation":
        _, failed = ex.pull_nibrs_estimation()
        return failed > 0
    return False


@app.command(name="promote")
def promote_cmd(
    staging: Annotated[Path, typer.Argument(help="The staging directory of a pull run.")],
    target: Annotated[Path, typer.Option("--target", help="The release directory.")] = RELEASE_DIR,
    merge: Annotated[
        bool,
        typer.Option("--merge", help="Replace only the partitions in the run (for a subset pull)."),
    ] = False,
    allow_shrink: Annotated[
        bool, typer.Option("--allow-shrink", help="Allow a domain to lose partitions.")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Check and report, but do not write the release.")
    ] = False,
) -> None:
    """Make a staging run the next release (coverage check, revision report, atomic swap)."""
    try:
        result = promote(staging, target, merge=merge, allow_shrink=allow_shrink, dry_run=dry_run)
    except PromoteError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None
    report = staging / "revisions.md"
    report.write_text(result.revisions)
    verb = "Would promote" if dry_run else "Promoted"
    typer.echo(f"{verb} release {result.release['release_id']} to {target}")
    typer.echo(f"  replaced: {', '.join(result.replaced) or '(none)'}")
    typer.echo(f"  kept:     {', '.join(result.kept) or '(none)'}")
    typer.echo(f"  revision report: {report}")


def main() -> None:
    try:
        app()
    except (CdeError, ValueError) as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
