"""Command facade for scraping Chanel Korea fragrance data."""

from __future__ import annotations

import json
import os
import random
import time
from pathlib import Path
from typing import Any

from pipelines.chanel_korea.category import extract_fragrance_products
from pipelines.chanel_korea.detail import extract_product_detail
from pipelines.chanel_korea.fetch import fetch_paginated_category as _fetch_paginated_category
from pipelines.common import build_request_headers, fetch_rendered_html, get_with_retries, normalize_product_rows, print_json_rows


DEFAULT_URL = "https://www.chanel.com/kr/fragrance/women/c/7x1x1/"


def build_headers() -> dict[str, str]:
    """Build request headers for Chanel Korea requests."""
    return build_request_headers("CHANEL_KR")


def fetch_category(
    url: str = DEFAULT_URL,
    *,
    use_selenium: bool | None = None,
    use_scrapling: bool | None = None,
) -> str:
    """Fetch Chanel Korea fragrance category HTML."""
    if use_selenium is None:
        use_selenium = _env_flag("CHANEL_KR_USE_SELENIUM")
    if use_selenium:
        return fetch_rendered_html(url)

    fetcher = _selected_fetcher()
    if fetcher in {"curl", "curl_cffi"}:
        return fetch_curl_cffi_html(url)

    if use_scrapling is None:
        use_scrapling = fetcher != "requests"
    if use_scrapling:
        return fetch_scrapling_html(url)

    response = get_with_retries(url, headers=build_headers(), timeout=20)
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.text


def fetch_curl_cffi_html(url: str = DEFAULT_URL) -> str:
    """Fetch HTML using curl_cffi's browser TLS impersonation."""
    from curl_cffi import requests as curl_requests

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": os.getenv("CHANEL_KR_ACCEPT_LANGUAGE", "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"),
        "Referer": "https://www.chanel.com/kr/",
        "Upgrade-Insecure-Requests": "1",
        **build_headers(),
    }
    last_error: Exception | None = None
    for impersonate in _curl_impersonates():
        try:
            response = curl_requests.get(url, impersonate=impersonate, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as error:
            last_error = error

    if last_error is None:
        raise RuntimeError("No curl_cffi impersonation values configured.")
    raise last_error


def fetch_scrapling_html(url: str = DEFAULT_URL) -> str:
    """Fetch HTML using the configured Scrapling fetcher mode."""
    from scrapling.fetchers import DynamicFetcher, Fetcher, StealthyFetcher

    mode = _selected_fetcher()
    timeout_ms = int(os.getenv("CHANEL_KR_SCRAPLING_TIMEOUT_MS", "20000"))
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
            impersonate=os.getenv("CHANEL_KR_SCRAPLING_IMPERSONATE", "chrome"),
            stealthy_headers=True,
            timeout=timeout_ms,
            headers=headers or None,
        )
    else:
        raise ValueError(
            "CHANEL_KR_FETCHER must be one of requests, curl, curl_cffi, scrapling, fetcher, static, dynamic, stealthy."
        )

    html = getattr(response, "html_content", "")
    return str(html)


def scrape_perfume_names(url: str = DEFAULT_URL) -> list[dict[str, str]]:
    """Scrape normalized Chanel Korea fragrance rows."""
    html = _fetch_paginated_category(url, fetch_page=fetch_category)
    rows = extract_fragrance_products(html)
    return _add_product_details(rows)


def fetch_product_detail(product_url: str) -> dict[str, Any]:
    """Fetch and parse Chanel Korea product detail fields."""
    if not product_url:
        return {"ingredients": "", "key_ingredients": []}
    return extract_product_detail(fetch_category(product_url))


def fetch_product_detail_safely(product_url: str) -> dict[str, Any]:
    """Fetch product details and return empty fields when the request is blocked."""
    try:
        return fetch_product_detail(product_url)
    except Exception as error:
        if not _allow_partial_results():
            raise
        print(f"Skipping Chanel detail after fetch error: {product_url} ({error})")
        return {"ingredients": "", "key_ingredients": []}


def main() -> None:
    """Run the Chanel Korea scraper and write the configured JSON output."""
    url = os.getenv("CHANEL_KR_HOME_URL", DEFAULT_URL)
    output_path = Path(os.getenv("CHANEL_KR_OUTPUT_PATH", "data/chanel_korea_fragrance_data.json"))
    rows = scrape_perfume_names(url)
    if not rows:
        raise RuntimeError("Chanel Korea scraper returned no fragrance rows; output was not written.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_rows = normalize_product_rows(
        rows,
        source="official",
        source_country="KR",
        brand="CHANEL",
        generate_description=False,
    )
    output_path.write_text(json.dumps(normalized_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print_json_rows(normalized_rows)


def _add_product_details(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    detail_by_url: dict[str, dict[str, Any]] = {}
    detailed_rows: list[dict[str, str]] = []
    for index, row in enumerate(_limited_rows(rows)):
        product_url = row.get("product_url", "")
        if product_url not in detail_by_url:
            if index:
                _sleep_between_requests()
            detail_by_url[product_url] = fetch_product_detail_safely(product_url)
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


def _limited_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    max_details = int(os.getenv("CHANEL_KR_MAX_DETAIL_PAGES", "0") or "0")
    if max_details <= 0:
        return rows
    return rows[:max_details]


def _sleep_between_requests() -> None:
    min_delay = float(os.getenv("CHANEL_KR_REQUEST_DELAY_SECONDS", "1.0") or "1.0")
    max_delay = float(os.getenv("CHANEL_KR_REQUEST_DELAY_MAX_SECONDS", str(min_delay)) or str(min_delay))
    if max_delay < min_delay:
        max_delay = min_delay
    if max_delay <= 0:
        return
    time.sleep(random.uniform(min_delay, max_delay))


def _allow_partial_results() -> bool:
    return _env_flag("CHANEL_KR_ALLOW_PARTIAL_RESULTS")


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _selected_fetcher() -> str:
    return os.getenv("CHANEL_KR_FETCHER", "curl_cffi").strip().lower()


def _curl_impersonates() -> list[str]:
    raw_values = os.getenv(
        "CHANEL_KR_CURL_IMPERSONATES",
        os.getenv("CHANEL_KR_CURL_IMPERSONATE", "safari17_2_ios,safari17_0,chrome124"),
    )
    return [value.strip() for value in raw_values.split(",") if value.strip()]


if __name__ == "__main__":
    main()

# End of file.
