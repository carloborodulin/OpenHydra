"""Write the OpenAPI document of the API to a file (for the web type check).

Usage: uv run python scripts/export_openapi.py ../web/openapi.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from openhydra_api.main import app


def main(target: str) -> None:
    doc = app.openapi()
    Path(target).write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    print(f"wrote {target} ({len(doc['paths'])} paths)")


if __name__ == "__main__":
    main(sys.argv[1])
