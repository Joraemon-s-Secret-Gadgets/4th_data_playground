"""Command facade for scraping Fraganty perfume data."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pipelines.common import fetch_rendered_html, normalize_product_rows, print_json_rows
from pipelines.fraganty.category import BASE_URL, extract_perfume_links
from pipelines.fraganty.detail import extract_perfume_detail, extract_review_detail


def fetch_brand_page(brand_slug: str) -> str:
    """Fetch a rendered Fraganty brand page."""
    return fetch_rendered_html(f"{BASE_URL}/brands/{brand_slug}")


def fetch_product_page(url: str) -> str:
    """Fetch a rendered Fraganty product or review page."""
    return fetch_rendered_html(url)


def scrape_perfume_links(brand_slug: str, *, fetch_page: Any = fetch_brand_page) -> list[str]:
    """Scrape perfume links for a Fraganty brand slug."""
    return extract_perfume_links(fetch_page(brand_slug))


def scrape_perfume_detail(brand: str, url: str, *, fetch_page: Any = fetch_product_page) -> dict[str, Any]:
    """Scrape one Fraganty perfume detail and its review prose."""
    row = extract_perfume_detail(fetch_page(url), brand=brand, url=url)
    review_url = url.replace("/perfume/", "/reviews/")
    row.update(extract_review_detail(fetch_page(review_url)))
    return row


def main() -> None:
    """Scrape one configured Fraganty brand and write raw detail JSON."""
    brand = os.getenv("FRAGANTY_BRAND", "Dior")
    brand_slug = os.getenv("FRAGANTY_BRAND_SLUG", brand)
    output_path = Path(os.getenv("FRAGANTY_OUTPUT_PATH", f"data/{brand.lower()}_fraganty_raw_data.json"))

    rows = [scrape_perfume_detail(brand, url) for url in scrape_perfume_links(brand_slug)]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_rows = normalize_product_rows(rows, source="fraganty", source_country="", brand=brand)
    output_path.write_text(json.dumps(normalized_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print_json_rows(normalized_rows)


if __name__ == "__main__":
    main()

# End of file.
