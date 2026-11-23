"""BUG-5: the root .env is found from a package directory; env vars win."""

from __future__ import annotations

from pathlib import Path

import pytest

from cdeclient.config import Settings, find_env_file

SYNTHETIC = "synthetic-test-key-0000"


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".env").write_text(f"FBI_CDE_API_KEY={SYNTHETIC}\n")
    (tmp_path / "api").mkdir()
    monkeypatch.delenv("FBI_CDE_API_KEY", raising=False)
    monkeypatch.delenv("OPENHYDRA_ENV_FILE", raising=False)
    return tmp_path


def _key(s: Settings) -> str | None:
    return s.api_key.get_secret_value() if s.api_key else None


def test_root_env_is_found_from_a_package_dir(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo / "api")
    assert find_env_file() == repo / ".env"
    assert _key(Settings()) == SYNTHETIC


def test_search_stops_at_the_repository_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".env").write_text("FBI_CDE_API_KEY=outside-the-repo\n")
    inner = tmp_path / "repo"
    (inner / ".git").mkdir(parents=True)
    monkeypatch.delenv("OPENHYDRA_ENV_FILE", raising=False)
    assert find_env_file(inner) is None


def test_process_env_wins(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo / "api")
    monkeypatch.setenv("FBI_CDE_API_KEY", "from-the-environment")
    assert _key(Settings()) == "from-the-environment"


def test_explicit_env_file(repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    other = tmp_path / "other.env"
    other.write_text("FBI_CDE_API_KEY=explicit-file\n")
    monkeypatch.setenv("OPENHYDRA_ENV_FILE", str(other))
    monkeypatch.chdir(repo / "api")
    assert _key(Settings()) == "explicit-file"
