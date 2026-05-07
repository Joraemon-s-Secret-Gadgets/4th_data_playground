"""Command facade for scraping Lush Korea fragrance data."""

from __future__ import annotations

import json
import os
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import requests

from pipelines.common import (
    build_request_headers,
    extract_product_remote_id as _extract_product_remote_id,
    get_with_retries as _get_with_retries,
    normalize_review as _normalize_review,
    print_json_rows,
)
from pipelines.lush_korea.category import (
    extract_homepage_fragrance_products,
    format_korean_product_name as _format_korean_product_name,
)
from pipelines.lush_korea.detail import extract_product_detail
from pipelines.lush_korea.fetch import fetch_paginated_homepage as _fetch_paginated_homepage
from pipelines.lush_korea.search import find_product_metadata as _find_product_metadata


DEFAULT_URL = "https://www.lush.co.kr/m/categories/index/56?sort=popularity"
BASE_URL = "https://www.lush.co.kr"
SEARCH_URL = "https://www.lush.co.kr/m/elasticsearch/autolist"
VREVIEW_REVIEWS_URL = "https://one.vreview.tv/api/embed/v2/417377ee-f4a0-4d0d-8e48-0dc58f216fb9/reviews"
VREVIEW_REVIEW_EXPAND = (
    "rating,created_at,helpful_count,user_nickname,product,upload_from,"
    "spray_username,title,text,media_contents,comments"
)


def build_headers() -> dict[str, str]:
    """Build request headers for Lush Korea requests."""
    return build_request_headers("LUSH_KR")


def fetch_homepage(
    url: str = DEFAULT_URL,
    *,
    driver_factory: Callable[[], Any] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    stable_iterations: int = 5,
    scroll_pause_seconds: float = 1.5,
    use_selenium: bool | None = None,
) -> str:
    """Fetch the Lush Korea fragrance page using static pagination or Selenium."""
    if use_selenium is None:
        use_selenium = driver_factory is not None or _env_flag("LUSH_KR_USE_SELENIUM")
    if not use_selenium:
        return _fetch_paginated_homepage(
            url,
            get_with_retries=_get_with_retries,
            build_headers=build_headers,
        )

    driver = (driver_factory or _create_chrome_driver)()

    try:
        driver.get(url)

        last_count = 0
        same_count = 0

        while same_count < stable_iterations:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            sleep(scroll_pause_seconds)

            items = driver.find_elements("css selector", "li.prdlist__item")
            current_count = len(items)

            if current_count == last_count:
                same_count += 1
            else:
                same_count = 0
                last_count = current_count

        return driver.page_source

    finally:
        driver.quit()


def _create_chrome_driver() -> Any:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    cache_path = os.getenv("SELENIUM_MANAGER_CACHE") or os.path.join(os.getcwd(), ".selenium-cache")
    os.environ.setdefault("SE_CACHE_PATH", cache_path)

    chrome_options = Options()
    if Path("/usr/bin/chromium").exists():
        chrome_options.binary_location = "/usr/bin/chromium"
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--remote-debugging-pipe")
    chrome_options.add_argument(f"--user-data-dir={tempfile.mkdtemp(prefix='lush-kr-chrome-')}")
    chrome_options.add_argument("--window-size=1920,1080")

    return webdriver.Chrome(options=chrome_options)


def scrape_perfume_names(url: str = DEFAULT_URL) -> list[dict[str, str]]:
    """Scrape normalized Lush Korea fragrance rows."""
    session = requests.Session()
    session.headers.update(build_headers())
    html = fetch_homepage(url)

    rows: list[dict[str, str]] = []
    for product in extract_homepage_fragrance_products(html):
        matched = find_product_metadata(session, product["korean_name"], product["product_type"])
        full_korean_name = _format_korean_product_name(product["korean_name"], product["product_type"])
        product_url = product.get("product_url") or matched.get("product_url", "")
        regular_price = product.get("regular_price") or matched.get("regular_price", "")
        detail = fetch_product_detail(session, product_url)
        # Reviews are temporarily disabled.
        # review_detail = fetch_product_reviews(session, matched.get("product_url", ""))
        rows.append(
            {
                "country": "KR",
                "korean_name": full_korean_name,
                "english_name": matched.get("english_name", ""),
                "product_type": product["product_type"],
                "product_url": product_url,
                "regular_price": regular_price,
                "image_url": product.get("image_url", ""),
                "ingredients": detail["ingredients"],
                "key_ingredients": detail["key_ingredients"],
                # "review_count": review_detail["review_count"],
                # "reviews": review_detail["reviews"],
            }
        )
    return rows


def find_product_metadata(
    session: requests.Session,
    korean_name: str,
    product_type: str,
) -> dict[str, str]:
    """Find metadata for a Lush Korea product through the search facade."""
    return _find_product_metadata(
        session,
        korean_name,
        product_type,
        search_url=SEARCH_URL,
        base_url=BASE_URL,
        get_with_retries=_get_with_retries,
    )


def fetch_product_detail(session: requests.Session, product_url: str) -> dict[str, Any]:
    """Fetch and parse product detail fields for a Lush Korea product URL."""
    if not product_url:
        return {"ingredients": "", "key_ingredients": []}

    response = _get_with_retries(session, product_url, timeout=20)
    response.raise_for_status()
    response.encoding = "utf-8"
    return extract_product_detail(response.text)


def fetch_product_reviews(session: requests.Session, product_url: str, limit: int = 100) -> dict[str, Any]:
    """Fetch normalized review data from the review provider API."""
    product_remote_id = _extract_product_remote_id(product_url)
    if not product_remote_id:
        return {"review_count": 0, "reviews": []}

    reviews: list[dict[str, Any]] = []
    review_count = 0
    offset = 0

    while True:
        response = _get_with_retries(
            session,
            VREVIEW_REVIEWS_URL,
            params={
                "product_remote_id": product_remote_id,
                "limit": limit,
                "offset": offset,
                "expand": VREVIEW_REVIEW_EXPAND,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        review_count = int(payload.get("count") or 0)
        batch = payload.get("results") or []
        reviews.extend(_normalize_review(review) for review in batch)

        offset += len(batch)
        if not batch or offset >= review_count:
            break

    return {"review_count": review_count, "reviews": reviews}


def main() -> None:
    """Run the Lush Korea scraper and write the configured JSON output."""
    url = os.getenv("LUSH_KR_HOME_URL", DEFAULT_URL)
    output_path = Path(os.getenv("LUSH_KR_OUTPUT_PATH", "data/lush_korea_fragrance_data.json"))
    rows = scrape_perfume_names(url)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print_json_rows(rows)


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    main()

# End of file.
