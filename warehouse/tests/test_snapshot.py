"""Staging runs, resume, partial failure, promotion and revision reports."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import polars as pl
import pytest
from cdeclient import CdeNotFound, CdeUpstreamError
from cdeclient.models import (
    HateCrimeResponse,
    SummarizedResponse,
    UofParticipation,
    UofQuestionItem,
)
from typer.testing import CliRunner

from openhydra_etl import snapshot
from openhydra_etl.cli import app
from openhydra_etl.extract import DomainFailed, Extractor
from openhydra_etl.snapshot import FILES, PromoteError, RunLog, promote


class FakeClient:
    """Counts calls; fails on chosen keys."""

    def __init__(self, sample: Callable[[str], Any], fail: dict[str, Exception] | None = None):
        self.sample = sample
        self.fail = fail or {}
        self.calls: Counter[str] = Counter()

    def _maybe_fail(self, key: str) -> None:
        self.calls[key] += 1
        if key in self.fail:
            raise self.fail[key]

    def summarized_national(self, off: str, f: str, t: str) -> SummarizedResponse:
        self._maybe_fail(f"US:{off}")
        return SummarizedResponse.model_validate(self.sample("summarized_national_homicide"))

    def summarized_state(self, st: str, off: str, f: str, t: str) -> SummarizedResponse:
        self._maybe_fail(f"{st}:{off}")
        return SummarizedResponse.model_validate(self.sample("summarized_state_NY_violent"))

    def hate_crime_national(self, f: str, t: str) -> HateCrimeResponse:
        self._maybe_fail("hate:US")
        return HateCrimeResponse.model_validate(self.sample("hate_crime_national_totals"))

    def hate_crime_state(self, st: str, f: str, t: str) -> HateCrimeResponse:
        self._maybe_fail(f"hate:{st}")
        return HateCrimeResponse.model_validate(self.sample("hate_crime_national_totals"))

    def uof_participation_national(self, yr: str) -> UofParticipation:
        self._maybe_fail(f"uofp:{yr}")
        return UofParticipation.from_payload(self.sample("uof_participation_national_2022"))

    def uof_questions(self, yr: str) -> list[UofQuestionItem]:
        self._maybe_fail(f"uofq:{yr}")
        return []


def _run(tmp: Path, states: list[str]) -> RunLog:
    return RunLog.load_or_new(
        tmp,
        run_id="20261123T000000Z",
        window={"from": "01-2015", "to": "12-2024"},
        states=states,
        client_version="test",
    )


def test_a_failed_request_writes_no_domain_file(tmp_path: Path, sample: Any) -> None:
    fake = FakeClient(sample, fail={"NY:homicide": CdeUpstreamError(503, "x")})
    run = _run(tmp_path, ["NY"])
    ex = Extractor(fake, tmp_path, run=run)  # type: ignore[arg-type]
    run.start("summarized")
    with pytest.raises(DomainFailed):
        ex.pull_summarized(["homicide", "rape"], ["NY"], "01-2015", "12-2024")
    assert not (tmp_path / "summarized.parquet").exists()
    reqs = run.domains["summarized"]["requests"]
    assert reqs["error"] == 1 and reqs["ok"] == 2  # US:homicide, US:rape before NY:homicide


def test_resume_reuses_parts(tmp_path: Path, sample: Any) -> None:
    flaky = FakeClient(sample, fail={"NY:rape": CdeUpstreamError(503, "x")})
    ex = Extractor(flaky, tmp_path)  # type: ignore[arg-type]
    with pytest.raises(DomainFailed):
        ex.pull_summarized(["homicide", "rape"], ["NY"], "01-2015", "12-2024")
    healthy = FakeClient(sample)
    ex2 = Extractor(healthy, tmp_path)  # type: ignore[arg-type]
    frame = ex2.pull_summarized(["homicide", "rape"], ["NY"], "01-2015", "12-2024")
    assert set(healthy.calls) == {"NY:rape"}  # only the missing part is fetched
    assert frame.height > 0


def test_uof_404_writes_neither_file(tmp_path: Path, sample: Any) -> None:
    fake = FakeClient(sample, fail={"uofp:2022": CdeNotFound(404, "participation")})
    ex = Extractor(fake, tmp_path)  # type: ignore[arg-type]
    with pytest.raises(DomainFailed, match="CdeNotFound"):
        ex.pull_uof(["2021", "2022"])
    assert not (tmp_path / "uof_participation.parquet").exists()
    assert not (tmp_path / "uof_questions.parquet").exists()


def test_pacing_spaces_requests(tmp_path: Path, sample: Any) -> None:
    now = [0.0]
    waits: list[float] = []

    def sleep(s: float) -> None:
        waits.append(s)
        now[0] += s

    ex = Extractor(FakeClient(sample), tmp_path, per_hour=3600, sleep=sleep, clock=lambda: now[0])  # type: ignore[arg-type]
    ex.pull_summarized(["homicide", "rape", "robbery"], [], "01-2015", "12-2024")
    assert waits == [1.0, 1.0]


# -- promotion ----------------------------------------------------------------
def _release(target: Path, frames: dict[str, pl.DataFrame]) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for name, spec in FILES.items():
        frame = frames.get(name, pl.DataFrame(schema=spec.schema))
        frame.write_parquet(target / spec.file)
    snapshot.write_json_atomic(
        target / snapshot.MANIFEST, {"kind": "release", "release_id": "old", "domains": {}}
    )


def _hate(areas: list[str], value: float = 1.0) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {"level": "state", "area": a, "category": "bias", "label": "x", "value": value}
            for a in areas
        ],
        schema=FILES["hate_crime"].schema,
    )


def _staging(tmp: Path, frame: pl.DataFrame, states: list[str]) -> Path:
    staging = tmp / "staging"
    staging.mkdir()
    frame.write_parquet(staging / "hate_crime.parquet")
    run = _run(staging, states)
    run.start("hate-crime")
    run.finish("hate-crime", [staging / "hate_crime.parquet"])
    return staging


def test_promote_replaces_a_domain_and_reports_revisions(tmp_path: Path) -> None:
    target = tmp_path / "seed"
    _release(target, {"hate_crime": _hate(["NY", "TX"], 1.0)})
    staging = _staging(tmp_path, _hate(["NY", "TX"], 2.0), ["NY", "TX"])
    result = promote(staging, target)
    assert result.replaced == ["hate_crime"]
    assert "values changed 2" in result.revisions
    manifest = json.loads((target / "_manifest.json").read_text())
    assert manifest["release_id"] == "20261123T000000Z"
    assert manifest["previous_release_id"] == "old"
    assert manifest["domains"]["hate_crime"]["rows"] == 2
    assert pl.read_parquet(target / "hate_crime.parquet")["value"].to_list() == [2.0, 2.0]
    assert not (tmp_path / ".seed.next").exists() and not (tmp_path / ".seed.prev").exists()


def test_promote_refuses_to_lose_partitions(tmp_path: Path) -> None:
    target = tmp_path / "seed"
    _release(target, {"hate_crime": _hate(["NY", "TX"])})
    staging = _staging(tmp_path, _hate(["NY"]), ["NY"])
    with pytest.raises(PromoteError, match="lose 1 partitions"):
        promote(staging, target)
    # The release is unchanged.
    assert pl.read_parquet(target / "hate_crime.parquet").height == 2


def test_promote_merge_replaces_only_the_run_partitions(tmp_path: Path) -> None:
    target = tmp_path / "seed"
    _release(target, {"hate_crime": _hate(["NY", "TX"], 1.0)})
    staging = _staging(tmp_path, _hate(["NY"], 5.0), ["NY"])
    promote(staging, target, merge=True)
    out = pl.read_parquet(target / "hate_crime.parquet").sort("area")
    assert out["area"].to_list() == ["NY", "TX"]
    assert out["value"].to_list() == [5.0, 1.0]


def test_promote_keeps_domains_that_the_run_did_not_complete(tmp_path: Path) -> None:
    target = tmp_path / "seed"
    _release(target, {"hate_crime": _hate(["NY"])})
    staging = tmp_path / "staging"
    staging.mkdir()
    run = _run(staging, ["NY"])
    run.start("hate-crime")
    run.fail("hate-crime", "upstream 503")
    result = promote(staging, target)
    assert result.replaced == []
    assert "hate_crime" in result.kept


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    target = tmp_path / "seed"
    _release(target, {"hate_crime": _hate(["NY"], 1.0)})
    staging = _staging(tmp_path, _hate(["NY"], 9.0), ["NY"])
    promote(staging, target, dry_run=True)
    assert pl.read_parquet(target / "hate_crime.parquet")["value"].to_list() == [1.0]


# -- CLI -------------------------------------------------------------------------
def test_cli_rejects_reversed_window_and_unknown_state() -> None:
    runner = CliRunner()
    r = runner.invoke(app, ["pull", "--from", "12-2024", "--to", "01-2015"])
    assert r.exit_code != 0 and "starts after" in r.output
    r = runner.invoke(app, ["pull", "--states", "NY,ZZ"])
    assert r.exit_code != 0 and "ZZ" in r.output


def test_repeated_states_are_pulled_once(
    tmp_path: Path, sample: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeClient(sample)

    class _Ctx:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        def __enter__(self) -> FakeClient:
            return fake

        def __exit__(self, *a: Any) -> None:
            return None

    monkeypatch.setattr("openhydra_etl.cli.CdeClient", _Ctx)
    r = CliRunner().invoke(
        app,
        [
            "pull",
            "--states",
            "NY,ny,NY",
            "--domains",
            "hate-crime",
            "--out",
            str(tmp_path),
            "--per-hour",
            "0",
        ],
    )
    assert r.exit_code == 0, r.output
    assert fake.calls["hate:NY"] == 1
    frame = pl.read_parquet(tmp_path / "hate_crime.parquet")
    assert (
        frame.filter(pl.col("area") == "NY").select(["category", "label"]).is_duplicated().sum()
        == 0
    )
    manifest = json.loads((tmp_path / "_manifest.json").read_text())
    assert manifest["states"] == ["NY"]
    assert manifest["domains"]["hate-crime"]["status"] == "ok"
