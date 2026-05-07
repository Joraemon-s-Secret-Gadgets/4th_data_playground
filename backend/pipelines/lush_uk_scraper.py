"""Command facade for scraping Lush UK fragrance data."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pipelines.common import (
    build_request_headers,
    fetch_rendered_html,
    get_with_retries,
    print_json_rows,
)
from pipelines.lush_uk.category import (
    extract_fragrance_products,
    extract_referenced_products,
    scrape_perfume_names_from_html,
)
from pipelines.lush_uk.detail import extract_product_detail, extract_product_price
from pipelines.lush_uk.search import (
    dedupe_products as _dedupe_products,
    extract_search_products,
    fetch_collection_products,
)


DEFAULT_URL = "https://www.lush.com/uk/en/c/fragrances"
BASE_URL = "https://www.lush.com"
FALLBACK_COLLECTION_URLS = (
    "https://www.lush.com/uk/en/c/cruelty-free-perfume",
    "https://www.lush.com/uk/en/c/body-sprays",
    "https://www.lush.com/uk/en/c/solid-perfume",
    "https://www.lush.com/uk/en/c/perfume-gifts",
)
SEARCH_COLLECTION_NAMES = ("Fragrances",)


def build_headers() -> dict[str, str]:
    """Build request headers for Lush UK requests."""
    return build_request_headers("LUSH_UK")


def fetch_category(
    url: str = DEFAULT_URL,
    *,
    use_selenium: bool | None = None,
    use_scrapling: bool | None = None,
) -> str:
    """Fetch Lush UK category HTML through the configured fetcher."""
    if use_selenium is None:
        use_selenium = _env_flag("LUSH_UK_USE_SELENIUM")
    if use_selenium:
        return fetch_rendered_html(url)

    if use_scrapling is None:
        use_scrapling = _selected_fetcher() != "requests"
    if use_scrapling:
        return fetch_scrapling_html(url)

    response = get_with_retries(url, headers=build_headers(), timeout=20)
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.text


def fetch_scrapling_html(url: str = DEFAULT_URL) -> str:
    """Fetch HTML using the configured Scrapling fetcher mode."""
    from scrapling.fetchers import DynamicFetcher, Fetcher, StealthyFetcher

    mode = _selected_fetcher()
    timeout_ms = int(os.getenv("LUSH_UK_SCRAPLING_TIMEOUT_MS", "20000"))
    headers = build_headers()

    if mode in {"stealth", "stealthy"}:
        response = StealthyFetcher.fetch(
            url,
            headless=True,
            network_idle=True,
            solve_cloudflare=True,
            timeout=timeout_ms,
            extra_headers=headers or None,
        )
    elif mode == "dynamic":
        response = DynamicFetcher.fetch(
            url,
            headless=True,
            network_idle=True,
            timeout=timeout_ms,
            extra_headers=headers or None,
        )
    elif mode in {"scrapling", "fetcher", "static"}:
        response = Fetcher.get(
            url,
            impersonate=os.getenv("LUSH_UK_SCRAPLING_IMPERSONATE", "chrome"),
            stealthy_headers=True,
            timeout=timeout_ms,
            headers=headers or None,
        )
    else:
        raise ValueError(
            "LUSH_UK_FETCHER must be one of requests, scrapling, fetcher, static, dynamic, stealthy."
        )

    html = getattr(response, "html_content", "")
    return str(html)


def scrape_perfume_names(url: str = DEFAULT_URL) -> list[dict[str, str]]:
    """Scrape normalized Lush UK fragrance rows."""
    if url == DEFAULT_URL:
        rows: list[dict[str, str]] = []
        for collection_name in SEARCH_COLLECTION_NAMES:
            rows.extend(fetch_collection_products(collection_name))
        return _add_product_details(_dedupe_products(rows))

    rows = scrape_perfume_names_from_html(fetch_category(url))
    if rows or url != DEFAULT_URL:
        return _add_product_details(_add_regular_prices(rows))

    for collection_url in FALLBACK_COLLECTION_URLS:
        rows.extend(scrape_perfume_names_from_html(fetch_category(collection_url)))
    return _add_product_details(_add_regular_prices(_dedupe_products(rows)))


def fetch_product_price(product_url: str) -> str:
    """Fetch and parse a Lush UK product's regular price."""
    if not product_url:
        return ""
    return extract_product_price(fetch_category(product_url))


def fetch_product_detail(product_url: str) -> dict[str, Any]:
    """Fetch and parse Lush UK product detail fields."""
    if not product_url:
        return {"ingredients": "", "key_ingredients": []}
    return extract_product_detail(fetch_category(product_url))


def main() -> None:
    """Run the Lush UK scraper and write the configured JSON output."""
    url = os.getenv("LUSH_UK_HOME_URL", DEFAULT_URL)
    output_path = Path(os.getenv("LUSH_UK_OUTPUT_PATH", "data/lush_uk_fragrance_data.json"))
    rows = scrape_perfume_names(url)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print_json_rows(rows)


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _selected_fetcher() -> str:
    return os.getenv("LUSH_UK_FETCHER", "scrapling").strip().lower()


def _add_regular_prices(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    price_by_url: dict[str, str] = {}
    priced_rows: list[dict[str, str]] = []
    for row in rows:
        product_url = row.get("product_url", "")
        if product_url not in price_by_url:
            price_by_url[product_url] = fetch_product_price(product_url)
        priced_rows.append({**row, "regular_price": price_by_url[product_url]})
    return priced_rows


def _add_product_details(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    detail_by_url: dict[str, dict[str, Any]] = {}
    detailed_rows: list[dict[str, str]] = []
    for row in rows:
        product_url = row.get("product_url", "")
        if product_url not in detail_by_url:
            detail_by_url[product_url] = fetch_product_detail(product_url)
        detail = detail_by_url[product_url]
        detailed_rows.append(
            {
                **row,
                "image_url": row.get("image_url", "") or str(detail.get("image_url") or ""),
                "ingredients": str(detail.get("ingredients") or ""),
                "key_ingredients": detail.get("key_ingredients") or [],
            }
        )
    return detailed_rows


if __name__ == "__main__":
    main()

# End of file.
