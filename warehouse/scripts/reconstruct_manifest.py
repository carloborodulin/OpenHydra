"""Write a release manifest for the seed that existed before manifests.

The seed in deploy/seed/ came from extracts in June 2026 that kept no
manifest. This script records what git history shows: the extraction date and
the window of each file. The manifest says "reconstructed": true, so no reader
takes these dates as exact extraction times.

Usage: uv run python scripts/reconstruct_manifest.py ../deploy/seed
"""

from __future__ import annotations

import sys
from pathlib import Path

from openhydra_etl.snapshot import FILES, MANIFEST, SOURCE, file_facts, utc_now, write_json_atomic

WINDOWED = {"from": "01-2015", "to": "12-2024"}
# Dates and windows from the git history of each file (commit in brackets).
HISTORY: dict[str, tuple[str, dict[str, str] | None, str]] = {
    "summarized": ("2026-06-11", WINDOWED, "01ab3b1"),
    "arrests": ("2026-06-11", WINDOWED, "01ab3b1; schema migrated in 1ea5153"),
    "pe": ("2026-06-11", {"from": "2015", "to": "2024"}, "01ab3b1"),
    "hate_crime": ("2026-06-11", WINDOWED, "01ab3b1"),
    "shr": ("2026-06-11", WINDOWED, "01ab3b1"),
    "property": ("2026-06-11", WINDOWED, "01ab3b1"),
    "nibrs": ("2026-06-11", WINDOWED, "01ab3b1"),
    "lesdc": ("2026-06-10", {"from": "2022", "to": "2023"}, "f6775cd"),
    "uof_participation": ("2026-06-10", {"from": "2019", "to": "2023"}, "b245da2"),
    "uof_questions": ("2026-06-10", {"from": "2019", "to": "2023"}, "b245da2"),
    "nibrs_estimation": ("2026-06-10", {"from": "2022", "to": "2022"}, "a24029f"),
    "agencies": ("2026-06-09", None, "4299875"),
}


def main(target: str) -> None:
    root = Path(target)
    domains = {}
    for name, spec in FILES.items():
        day, window, commit = HISTORY[name]
        domains[name] = {
            **file_facts(root / spec.file, spec),
            "run_id": None,
            "extracted_at": f"{day}T00:00:00Z",
            "window": window,
            "status": "reconstructed",
            "note": f"from git history ({commit})",
        }
    dates = sorted(d["extracted_at"] for d in domains.values())
    write_json_atomic(
        root / MANIFEST,
        {
            "schema_version": 1,
            "kind": "release",
            "release_id": "2026-06-11-reconstructed",
            "previous_release_id": None,
            "promoted_at": utc_now(),
            "source": SOURCE,
            "reconstructed": True,
            "window": WINDOWED,
            "extracted_at_min": dates[0],
            "extracted_at_max": dates[-1],
            "domains": domains,
        },
    )
    print(f"wrote {root / MANIFEST}")


if __name__ == "__main__":
    main(sys.argv[1])
