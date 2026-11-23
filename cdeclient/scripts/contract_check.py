"""Check that the FBI CDE routes the extract depends on still answer as expected.

Two requests: the national UoF participation route (it returned 404 at the
2026-11-22 audit) and one national summarized series. Exit 1 on a change.
Error messages never hold the API key.

Usage: uv run python scripts/contract_check.py
"""

from __future__ import annotations

import sys

from cdeclient import BULK, CdeClient, CdeError


def main() -> int:
    problems = []
    with CdeClient(policy=BULK) as client:
        try:
            p = client.uof_participation_national(2022)
            if p.data_year != 2022:
                problems.append("UoF participation 2022: no record")
        except CdeError as exc:
            problems.append(f"UoF participation 2022: {exc}")
        try:
            s = client.summarized_national("homicide", "01-2023", "12-2023")
            if not s.offenses.actuals:
                problems.append("summarized national homicide 2023: no actual counts")
        except CdeError as exc:
            problems.append(f"summarized national homicide 2023: {exc}")
    for line in problems:
        print(f"FAIL {line}")
    if not problems:
        print("The FBI routes answer as expected.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
