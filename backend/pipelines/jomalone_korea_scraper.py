"""Command facade for scraping Jo Malone Korea fragrance data."""

from __future__ import annotations

import json
import os
import random
import time
from pathlib import Path
from typing import Any

from pipelines.common import build_request_headers, get_with_retries, print_json_rows
from pipelines.jomalone_korea.category import extract_fragrance_products
from pipelines.jomalone_korea.detail import extract_product_detail


DEFAULT_URL = "https://www.jomalone.co.kr/colognes"


def build_headers() -> dict[str, str]:
    """Build request headers for Jo Malone Korea requests."""
    return {
        "Accept-Language": os.getenv("JOMALONE_KR_ACCEPT_LANGUAGE", "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"),
        "Referer": "https://www.jomalone.co.kr/",
        **build_request_headers("JOMALONE_KR"),
    }


def fetch_page(url: str = DEFAULT_URL) -> str:
    """Fetch Jo Malone Korea HTML using the selected fetcher."""
    fetcher = os.getenv("JOMALONE_KR_FETCHER", "curl_cffi").strip().lower()
    if fetcher in {"curl", "curl_cffi"}:
        return fetch_curl_cffi_html(url)

    response = get_with_retries(url, headers=build_headers(), timeout=30)
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.text


def fetch_curl_cffi_html(url: str = DEFAULT_URL) -> str:
    """Fetch Jo Malone Korea HTML using curl_cffi browser impersonation."""
    from curl_cffi import requests as curl_requests

    last_error: Exception | None = None
    for impersonate in _curl_impersonates():
        try:
            response = curl_requests.get(url, impersonate=impersonate, headers=build_headers(), timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as error:
            last_error = error

    if last_error is None:
        raise RuntimeError("No Jo Malone Korea curl_cffi impersonation values configured.")
    raise last_error


def scrape_perfume_names(url: str = DEFAULT_URL) -> list[dict[str, Any]]:
    """Scrape normalized Jo Malone Korea fragrance rows."""
    rows = extract_fragrance_products(fetch_page(url))
    return _add_product_details(rows)


def fetch_product_detail(product_url: str, preferred_size: str = "") -> dict[str, Any]:
    """Fetch and parse detail fields for a Jo Malone Korea product URL."""
    if not product_url:
        return {
            "korean_name": "",
            "english_name": "",
            "product_type": "",
            "regular_price": "",
            "image_url": "",
            "ingredients": "",
            "key_ingredients": [],
        }
    return extract_product_detail(fetch_page(product_url), preferred_size=preferred_size)


def main() -> None:
    """Run the Jo Malone Korea scraper and write the configured JSON output."""
    url = os.getenv("JOMALONE_KR_HOME_URL", DEFAULT_URL)
    output_path = Path(os.getenv("JOMALONE_KR_OUTPUT_PATH", "data/jomalone_korea_fragrance_data.json"))
    rows = scrape_perfume_names(url)
    if not rows:
        raise RuntimeError("Jo Malone Korea scraper returned no fragrance rows; output was not written.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print_json_rows(rows)


def _add_product_details(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    detailed_rows: list[dict[str, Any]] = []
    for index, row in enumerate(_limited_rows(rows)):
        if index:
            _sleep_between_requests()
        detail = fetch_product_detail(row.get("product_url", ""), row.get("size", ""))
        detailed_row = {
            "country": "KR",
            "korean_name": str(detail.get("korean_name") or row.get("korean_name") or ""),
            "english_name": str(detail.get("english_name") or row.get("english_name") or ""),
            "product_type": str(detail.get("product_type") or row.get("product_type") or ""),
            "product_url": row.get("product_url", ""),
            "regular_price": str(detail.get("regular_price") or row.get("regular_price") or ""),
            "image_url": str(detail.get("image_url") or row.get("image_url") or ""),
            "ingredients": str(detail.get("ingredients") or ""),
            "key_ingredients": detail.get("key_ingredients") or [],
        }
        detailed_rows.append(detailed_row)
    return detailed_rows


def _limited_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    max_details = int(os.getenv("JOMALONE_KR_MAX_DETAIL_PAGES", "0") or "0")
    if max_details <= 0:
        return rows
    return rows[:max_details]


def _sleep_between_requests() -> None:
    min_delay = float(os.getenv("JOMALONE_KR_REQUEST_DELAY_SECONDS", "0") or "0")
    max_delay = float(os.getenv("JOMALONE_KR_REQUEST_DELAY_MAX_SECONDS", str(min_delay)) or str(min_delay))
    if max_delay < min_delay:
        max_delay = min_delay
    if max_delay <= 0:
        return
    time.sleep(random.uniform(min_delay, max_delay))


def _curl_impersonates() -> list[str]:
    raw_values = os.getenv(
        "JOMALONE_KR_CURL_IMPERSONATES",
        os.getenv("JOMALONE_KR_CURL_IMPERSONATE", "safari17_2_ios,safari17_0,chrome124"),
    )
    return [value.strip() for value in raw_values.split(",") if value.strip()]


if __name__ == "__main__":
    main()

# End of file.
