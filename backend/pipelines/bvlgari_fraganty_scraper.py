"""Command facade for Bvlgari perfume data sourced from Fraganty."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pipelines.common import print_json_rows
from pipelines.fraganty_scraper import scrape_perfume_detail, scrape_perfume_links


BRAND = "Bvlgari"
BRAND_SLUG = "bvlgari"
DEFAULT_OUTPUT_PATH = "data/bvlgari_fraganty_fragrance_data.json"


def scrape_perfume_names(*, links: list[str] | None = None) -> list[dict[str, Any]]:
    """Scrape raw Bvlgari perfume rows from Fraganty."""
    urls = links if links is not None else scrape_perfume_links(BRAND_SLUG)
    return [scrape_perfume_detail(BRAND, url) for url in urls]


def main() -> None:
    """Run the Bvlgari Fraganty scraper and write JSON output."""
    output_path = Path(os.getenv("BVLGARI_FRAGANTY_OUTPUT_PATH", DEFAULT_OUTPUT_PATH))
    rows = scrape_perfume_names()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print_json_rows(rows)


if __name__ == "__main__":
    main()

# End of file.
