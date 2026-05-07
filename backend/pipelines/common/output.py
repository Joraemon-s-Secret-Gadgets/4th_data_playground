"""Console output helpers for scraper command modules."""

from __future__ import annotations

import json
import sys
from typing import Any


def print_json_rows(rows: list[dict[str, Any]]) -> None:
    """Print scraped rows as UTF-8 JSON."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except ValueError:
            pass
    print(json.dumps(rows, ensure_ascii=False, indent=2))

# End of file.
