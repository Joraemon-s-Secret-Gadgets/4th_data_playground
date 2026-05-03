from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time
from html import unescape
from typing import Any

import requests


DriverFactory = Any


def build_request_headers(env_prefix: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    raw_headers = os.getenv(f"{env_prefix}_REQUEST_HEADERS")

    if raw_headers:
        parsed = json.loads(raw_headers)
        if not isinstance(parsed, dict):
            raise ValueError(f"{env_prefix}_REQUEST_HEADERS must be a JSON object.")
        headers.update({str(key): str(value) for key, value in parsed.items()})

    if user_agent := os.getenv(f"{env_prefix}_USER_AGENT"):
        headers["User-Agent"] = user_agent

    if accept_language := os.getenv(f"{env_prefix}_ACCEPT_LANGUAGE"):
        headers["Accept-Language"] = accept_language

    return headers


def get_with_retries(
    session_or_url: requests.Session | str,
    url: str | None = None,
    *,
    retries: int = 3,
    backoff_seconds: float = 0.5,
    **kwargs: Any,
) -> requests.Response:
    if isinstance(session_or_url, requests.Session):
        session = session_or_url
        request_url = url
    else:
        session = requests
        request_url = session_or_url

    if request_url is None:
        raise ValueError("request URL is required.")

    last_error: requests.RequestException | None = None
    for attempt in range(retries):
        try:
            return session.get(request_url, **kwargs)
        except requests.RequestException as error:
            last_error = error
            if attempt == retries - 1:
                break
            time.sleep(backoff_seconds * (attempt + 1))

    if last_error is None:
        raise RuntimeError("request failed without an exception.")
    raise last_error


def fetch_rendered_html(
    url: str,
    *,
    driver_factory: DriverFactory | None = None,
    wait_seconds: float = 5,
) -> str:
    driver = (driver_factory or _create_default_webdriver)()
    try:
        driver.get(url)
        time.sleep(wait_seconds)
        return str(driver.page_source)
    finally:
        driver.quit()


def extract_product_remote_id(product_url: str) -> str:
    if match := re.search(r"/products/view/([^/?#]+)", product_url):
        return match.group(1)
    if match := re.search(r"/(\d+)(?:[/?#]|$)", product_url):
        return match.group(1)
    return ""


def normalize_review(review: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": review.get("id"),
        "title": normalize_text(str(review.get("title") or "")),
        "text": normalize_text(str(review.get("text") or "")),
        "rating": review.get("rating"),
        "created_at": str(review.get("created_at") or ""),
        "user_nickname": str(review.get("user_nickname") or ""),
        "helpful_count": review.get("helpful_count") or 0,
        "selected_options": review.get("selected_options") or [],
        "media_count": review.get("media_count") or 0,
    }


def print_json_rows(rows: list[dict[str, Any]]) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except ValueError:
            pass
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def strip_tags(value: str) -> str:
    return normalize_text(re.sub(r"<[^>]+>", "", unescape(value)))


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _create_default_webdriver() -> Any:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    cache_path = os.getenv("SELENIUM_MANAGER_CACHE") or os.path.join(os.getcwd(), ".selenium-cache")
    os.environ.setdefault("SE_CACHE_PATH", cache_path)

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1440,1200")
    options.add_argument(f"--user-data-dir={tempfile.mkdtemp(prefix='selenium-chrome-')}")
    return webdriver.Chrome(options=options)
