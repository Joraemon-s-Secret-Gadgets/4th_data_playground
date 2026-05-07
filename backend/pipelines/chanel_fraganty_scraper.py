"""Command facade for Chanel perfume data sourced from Fraganty."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pipelines.common import normalize_product_rows, print_json_rows
from pipelines.fraganty_scraper import scrape_perfume_detail, scrape_perfume_links


BRAND = "Chanel"
BRAND_SLUG = "Chanel"
DEFAULT_OUTPUT_PATH = "data/chanel_fraganty_fragrance_data.json"


def scrape_perfume_names(*, links: list[str] | None = None) -> list[dict[str, Any]]:
    """Scrape raw Chanel perfume rows from Fraganty."""
    urls = links if links is not None else scrape_perfume_links(BRAND_SLUG)
    return [scrape_perfume_detail(BRAND, url) for url in urls]


def main() -> None:
    """Run the Chanel Fraganty scraper and write JSON output."""
    output_path = Path(os.getenv("CHANEL_FRAGANTY_OUTPUT_PATH", DEFAULT_OUTPUT_PATH))
    rows = scrape_perfume_names()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_rows = normalize_product_rows(rows, source="fraganty", source_country="FR", brand=BRAND)
    output_path.write_text(json.dumps(normalized_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print_json_rows(normalized_rows)


if __name__ == "__main__":
    main()

# End of file.
