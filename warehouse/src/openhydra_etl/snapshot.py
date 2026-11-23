"""Versioned snapshots: run manifests, coverage checks, revision reports, promotion.

An extract run writes to its own staging directory, with a ``_manifest.json``
that records each request's outcome. ``promote`` then builds the next release
from the staging files and the current release:

1. A domain that the run completed replaces the domain in the release. With
   ``merge=True`` it replaces only the partitions it holds.
2. A domain that the run did not complete stays as it was.
3. A domain may not lose a partition (for example a state) unless
   ``allow_shrink=True``.
4. ``revisions.md`` lists the values that changed since the last release.
5. The new files and the release manifest replace the release directory in
   one rename, so a reader never sees half a release.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from . import normalize

MANIFEST = "_manifest.json"
REVISIONS = "revisions.md"
SOURCE = "FBI Crime Data Explorer API (api.usa.gov/crime/fbi/cde)"


@dataclass(frozen=True)
class FileSpec:
    """One Parquet file of a release."""

    name: str
    schema: dict[str, pl.DataType]
    partition: tuple[str, ...]
    key: tuple[str, ...] | None = None  # None: every column except "value"

    @property
    def file(self) -> str:
        return f"{self.name}.parquet"

    def key_columns(self, frame: pl.DataFrame) -> list[str]:
        if self.key is not None:
            return list(self.key)
        return [c for c in frame.columns if c != "value"]


FILES: dict[str, FileSpec] = {
    spec.name: spec
    for spec in (
        FileSpec("summarized", normalize.SUMMARIZED_SCHEMA, ("level", "area", "offense")),
        FileSpec("agencies", normalize.AGENCIES_SCHEMA, ("state_abbr",), key=("ori",)),
        FileSpec("arrests", normalize.ARRESTS_SCHEMA, ("level", "area", "offense")),
        FileSpec("pe", normalize.PE_SCHEMA, ("level", "area")),
        FileSpec("hate_crime", normalize.HATE_CRIME_SCHEMA, ("level", "area")),
        FileSpec("shr", normalize.SHR_SCHEMA, ("level", "area")),
        FileSpec("property", normalize.PROPERTY_SCHEMA, ("level", "area", "offense", "year")),
        FileSpec("nibrs", normalize.NIBRS_SCHEMA, ("level", "area", "offense")),
        FileSpec("lesdc", normalize.LESDC_SCHEMA, ("year", "chart_type")),
        FileSpec("uof_participation", normalize.UOF_PARTICIPATION_SCHEMA, ("year",), key=("year",)),
        FileSpec("uof_questions", normalize.UOF_QUESTIONS_SCHEMA, ("year",)),
        FileSpec(
            "nibrs_estimation", normalize.NIBRS_ESTIMATION_SCHEMA, ("level", "area", "offense")
        ),
    )
}

# CLI domain name -> the release files it writes.
DOMAIN_FILES: dict[str, tuple[str, ...]] = {
    "summarized": ("summarized",),
    "agencies": ("agencies",),
    "arrests": ("arrests",),
    "pe": ("pe",),
    "hate-crime": ("hate_crime",),
    "shr": ("shr",),
    "property": ("property",),
    "nibrs": ("nibrs",),
    "lesdc": ("lesdc",),
    "uof": ("uof_participation", "uof_questions"),
    "nibrs-estimation": ("nibrs_estimation",),
}


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json_atomic(path: Path, data: Any) -> None:
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)


def write_parquet_atomic(frame: pl.DataFrame, path: Path) -> None:
    tmp = path.with_name(f".{path.name}.tmp")
    frame.write_parquet(tmp)
    os.replace(tmp, path)


def read_manifest(directory: Path) -> dict[str, Any] | None:
    path = directory / MANIFEST
    return json.loads(path.read_text()) if path.is_file() else None


def partitions(frame: pl.DataFrame, spec: FileSpec) -> set[tuple[Any, ...]]:
    cols = [c for c in spec.partition if c in frame.columns]
    if not cols or frame.height == 0:
        return set()
    return set(frame.select(cols).unique().iter_rows())


def file_facts(path: Path, spec: FileSpec) -> dict[str, Any]:
    frame = pl.read_parquet(path)
    return {
        "file": spec.file,
        "rows": frame.height,
        "partitions": len(partitions(frame, spec)),
        "sha256": sha256(path),
    }


# -- run manifest (one extract run) ----------------------------------------
@dataclass
class RunLog:
    """The manifest of one extract run. It is written after each domain."""

    directory: Path
    run_id: str
    window: dict[str, str]
    states: list[str]
    client_version: str
    started_at: str = field(default_factory=utc_now)
    domains: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def load_or_new(
        cls,
        directory: Path,
        *,
        run_id: str,
        window: dict[str, str],
        states: list[str],
        client_version: str,
    ) -> RunLog:
        old = read_manifest(directory)
        log = cls(directory, run_id, window, states, client_version)
        if old is not None:
            if old.get("window") != window or old.get("states") != states:
                raise ValueError(
                    "The staging directory holds a run with another window or state list."
                )
            log.run_id = old["run_id"]
            log.started_at = old["started_at"]
            log.domains = old.get("domains", {})
        return log

    def _domain(self, domain: str) -> dict[str, Any]:
        return self.domains.setdefault(
            domain,
            {"status": "running", "requests": {"ok": 0, "empty": 0, "error": 0}, "errors": []},
        )

    def record(self, domain: str, key: str, outcome: str, error: str | None = None) -> None:
        d = self._domain(domain)
        d["requests"][outcome] = d["requests"].get(outcome, 0) + 1
        if error is not None and len(d["errors"]) < 50:
            d["errors"].append({"key": key, "error": error})

    def start(self, domain: str) -> None:
        d = self._domain(domain)
        d["status"] = "running"
        d["requests"] = {"ok": 0, "empty": 0, "error": 0}
        d["errors"] = []
        self.save()

    def finish(self, domain: str, files: Iterable[Path], *, partial: bool = False) -> None:
        d = self._domain(domain)
        d["status"] = "partial" if partial else "ok"
        d["extracted_at"] = utc_now()
        d["files"] = {p.stem: file_facts(p, FILES[p.stem]) for p in files}
        self.save()

    def fail(self, domain: str, reason: str) -> None:
        d = self._domain(domain)
        d["status"] = "failed"
        d["reason"] = reason
        self.save()

    def save(self) -> None:
        write_json_atomic(
            self.directory / MANIFEST,
            {
                "schema_version": 1,
                "kind": "run",
                "run_id": self.run_id,
                "started_at": self.started_at,
                "updated_at": utc_now(),
                "client_version": self.client_version,
                "source": SOURCE,
                "window": self.window,
                "states": self.states,
                "domains": self.domains,
            },
        )


# -- promotion ----------------------------------------------------------------
class PromoteError(RuntimeError):
    """The staging run cannot become a release."""


@dataclass
class PromoteResult:
    release: dict[str, Any]
    revisions: str
    replaced: list[str]
    kept: list[str]


def _check_schema(frame: pl.DataFrame, spec: FileSpec) -> None:
    missing = [c for c in spec.schema if c not in frame.columns]
    if missing:
        raise PromoteError(f"{spec.file}: missing columns {missing}")


def _merge(old: pl.DataFrame, new: pl.DataFrame, spec: FileSpec) -> pl.DataFrame:
    """Replace only the partitions that ``new`` holds."""
    cols = [c for c in spec.partition if c in new.columns]
    if not cols or old.height == 0:
        return new
    kept = old.join(new.select(cols).unique(), on=cols, how="anti")
    return pl.concat([kept.select(new.columns), new], how="vertical_relaxed")


def revision_report(old: pl.DataFrame | None, new: pl.DataFrame, spec: FileSpec) -> list[str]:
    """Markdown lines that describe the change of one file."""
    lines = [f"### {spec.file}", ""]
    if old is None:
        lines += [f"New file: {new.height} rows.", ""]
        return lines
    key = [c for c in spec.key_columns(new) if c in old.columns]
    value_cols = [c for c in new.columns if c not in key and c in old.columns]
    o = old.select(key + value_cols).unique(subset=key, keep="last")
    n = new.select(key + value_cols).unique(subset=key, keep="last")
    added = n.join(o, on=key, how="anti").height
    removed = o.join(n, on=key, how="anti").height
    both = n.join(o, on=key, how="inner", suffix="_old")
    changed_mask = pl.lit(False)
    for c in value_cols:
        changed_mask = changed_mask | (pl.col(c).ne_missing(pl.col(f"{c}_old")))
    changed = both.filter(changed_mask)
    lines.append(
        f"Rows {old.height} -> {new.height}. Keys added {added}, removed {removed}, "
        f"values changed {changed.height}."
    )
    if "value" in value_cols and changed.height:
        top = (
            changed.with_columns(
                (pl.col("value") - pl.col("value_old")).alias("delta"),
            )
            .with_columns(pl.col("delta").abs().alias("abs_delta"))
            .sort("abs_delta", descending=True)
            .head(10)
        )
        lines += [
            "",
            "| " + " | ".join(key) + " | old | new | change |",
            "|" + "---|" * (len(key) + 3),
        ]
        for row in top.iter_rows(named=True):
            old_v, new_v = row["value_old"], row["value"]
            rel = f" ({(new_v - old_v) / old_v:+.1%})" if old_v else ""
            cells = [str(row[k]) for k in key]
            lines.append(
                "| "
                + " | ".join(cells)
                + f" | {old_v:,.2f} | {new_v:,.2f} | {new_v - old_v:+,.2f}{rel} |"
            )
    lines.append("")
    return lines


def promote(
    staging: Path,
    target: Path,
    *,
    merge: bool = False,
    allow_shrink: bool = False,
    dry_run: bool = False,
) -> PromoteResult:
    run = read_manifest(staging)
    if run is None or run.get("kind") != "run":
        raise PromoteError(f"{staging} has no run manifest")
    current = read_manifest(target) or {"domains": {}}

    next_dir = target.with_name(f".{target.name}.next")
    if next_dir.exists():
        shutil.rmtree(next_dir)
    next_dir.mkdir(parents=True)

    report = [
        f"# Revisions in release {run['run_id']}",
        "",
        f"Compared with release {current.get('release_id', '(none)')}.",
        "",
    ]
    replaced: list[str] = []
    kept: list[str] = []
    domains: dict[str, Any] = {}
    completed = {
        name
        for dom, info in run["domains"].items()
        if info.get("status") in ("ok", "partial")
        for name in DOMAIN_FILES[dom]
    }
    run_status = {name: dom for dom, info in run["domains"].items() for name in DOMAIN_FILES[dom]}

    for name, spec in FILES.items():
        old_path = target / spec.file
        old = pl.read_parquet(old_path) if old_path.is_file() else None
        if name in completed:
            new = pl.read_parquet(staging / spec.file)
            _check_schema(new, spec)
            if merge and old is not None:
                new = _merge(old, new, spec)
            if old is not None and not allow_shrink:
                lost = partitions(old, spec) - partitions(new, spec)
                if lost:
                    sample = sorted(map(str, lost))[:10]
                    raise PromoteError(
                        f"{spec.file} would lose {len(lost)} partitions, for example "
                        f"{sample}. Pull them again, use --merge, or pass --allow-shrink."
                    )
            write_parquet_atomic(new, next_dir / spec.file)
            report += revision_report(old, new, spec)
            dom = run_status[name]
            info = run["domains"][dom]
            domains[name] = {
                **file_facts(next_dir / spec.file, spec),
                "run_id": run["run_id"],
                "extracted_at": info["extracted_at"],
                "window": run["window"],
                "status": info["status"],
                "merged": merge,
            }
            replaced.append(name)
        elif old is not None:
            shutil.copy2(old_path, next_dir / spec.file)
            domains[name] = current["domains"].get(name, file_facts(old_path, spec))
            kept.append(name)
        else:
            raise PromoteError(f"{spec.file} is in neither the run nor the current release")

    extracted = sorted(d["extracted_at"] for d in domains.values() if d.get("extracted_at"))
    summarized_window = domains.get("summarized", {}).get("window") or run["window"]
    release = {
        "schema_version": 1,
        "kind": "release",
        "release_id": run["run_id"],
        "previous_release_id": current.get("release_id"),
        "promoted_at": utc_now(),
        "source": SOURCE,
        "reconstructed": False,
        "window": summarized_window,
        "extracted_at_min": extracted[0] if extracted else None,
        "extracted_at_max": extracted[-1] if extracted else None,
        "domains": domains,
    }
    revisions = "\n".join(report)
    write_json_atomic(next_dir / MANIFEST, release)
    (next_dir / REVISIONS).write_text(revisions)

    if dry_run:
        shutil.rmtree(next_dir)
    else:
        swap(next_dir, target)
    return PromoteResult(release, revisions, replaced, kept)


def swap(next_dir: Path, target: Path) -> None:
    """Put ``next_dir`` in place of ``target`` with renames (no half state)."""
    prev = target.with_name(f".{target.name}.prev")
    if prev.exists():
        shutil.rmtree(prev)
    if target.exists():
        os.replace(target, prev)
    os.replace(next_dir, target)
    if prev.exists():
        shutil.rmtree(prev)
