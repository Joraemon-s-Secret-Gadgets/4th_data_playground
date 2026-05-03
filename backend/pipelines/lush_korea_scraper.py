from __future__ import annotations

import json
import os
import re
from html import unescape
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup


DEFAULT_URL = "https://www.lush.co.kr/"
BASE_URL = "https://www.lush.co.kr"
SEARCH_URL = "https://www.lush.co.kr/m/elasticsearch/autolist"
PRODUCT_TYPES = {"보디 스프레이", "바디 스프레이", "퍼퓸", "솔리드 퍼퓸", "워시 카드", "캔들"}


def build_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    raw_headers = os.getenv("LUSH_KR_REQUEST_HEADERS")

    if raw_headers:
        parsed = json.loads(raw_headers)
        if not isinstance(parsed, dict):
            raise ValueError("LUSH_KR_REQUEST_HEADERS must be a JSON object.")
        headers.update({str(key): str(value) for key, value in parsed.items()})

    if user_agent := os.getenv("LUSH_KR_USER_AGENT"):
        headers["User-Agent"] = user_agent

    if accept_language := os.getenv("LUSH_KR_ACCEPT_LANGUAGE"):
        headers["Accept-Language"] = accept_language

    return headers


def extract_homepage_fragrance_products(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    fragrance_heading = soup.find("h2", class_="tit", string=lambda value: _normalize_text(value or "") == "프래그런스")
    if fragrance_heading is None:
        return []

    section = fragrance_heading.find_parent("div", class_="swiper-slide")
    if section is None:
        return []

    products: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for caption in section.select("figcaption.txt"):
        values = [_normalize_text(text) for text in caption.stripped_strings]
        values = [value for value in values if value]
        if len(values) < 2:
            continue

        product = {"korean_name": values[0], "product_type": values[1]}
        if product["product_type"] not in PRODUCT_TYPES:
            continue

        key = (product["korean_name"], product["product_type"])
        if key not in seen:
            products.append(product)
            seen.add(key)
    return products


def fetch_homepage(url: str = DEFAULT_URL) -> str:
    response = requests.get(url, headers=build_headers(), timeout=20)
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.text


def scrape_perfume_names(url: str = DEFAULT_URL) -> list[dict[str, str]]:
    session = requests.Session()
    session.headers.update(build_headers())
    html = fetch_homepage(url)

    rows: list[dict[str, str]] = []
    for product in extract_homepage_fragrance_products(html):
        matched = find_product_metadata(session, product["korean_name"], product["product_type"])
        full_korean_name = _format_korean_product_name(product["korean_name"], product["product_type"])
        rows.append(
            {
                "country": "KR",
                "korean_name": full_korean_name,
                "english_name": matched.get("english_name", ""),
                "product_type": product["product_type"],
                "product_url": matched.get("product_url", ""),
            }
        )
    return rows


def find_product_metadata(
    session: requests.Session,
    korean_name: str,
    product_type: str,
) -> dict[str, str]:
    for query in (f"{korean_name} {product_type}", korean_name):
        response = session.get(SEARCH_URL, params={"query": query}, timeout=20)
        response.raise_for_status()
        response.encoding = "utf-8"

        items = response.json().get("info", {}).get("item", [])
        if match := _select_search_result(items, korean_name, product_type):
            item_code = str(match.get("itemUserCode") or match.get("itemCode") or "")
            return {
                "english_name": _normalize_text(str(match.get("itemEName") or "")),
                "product_url": f"{BASE_URL}/products/view/{item_code}" if item_code else "",
            }

    return {"english_name": "", "product_url": ""}


def main() -> None:
    url = os.getenv("LUSH_KR_HOME_URL", DEFAULT_URL)
    output_path = Path(os.getenv("LUSH_KR_OUTPUT_PATH", "data/lush_korea_perfume_names.json"))
    rows = scrape_perfume_names(url)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def _select_search_result(
    items: list[dict[str, Any]],
    korean_name: str,
    product_type: str,
) -> dict[str, Any] | None:
    scored: list[tuple[int, dict[str, Any]]] = []
    target_full_name = _normalize_text(f"{korean_name} {product_type}")

    for item in items:
        item_name = _strip_tags(str(item.get("itemName") or item.get("highlightItemName") or ""))
        item_range = _normalize_text(str(item.get("itemRange") or ""))
        if korean_name not in item_name:
            continue

        score = 0
        if item_range == product_type:
            score += 8
        if item_name == korean_name:
            score += 4
        if item_name == target_full_name:
            score += 6
        if item_name.startswith(korean_name):
            score += 2
        if item.get("itemEName"):
            score += 1

        if score >= 8:
            scored.append((score, item))

    if not scored:
        return None
    return max(scored, key=lambda pair: pair[0])[1]


def _strip_tags(value: str) -> str:
    return _normalize_text(re.sub(r"<[^>]+>", "", unescape(value)))


def _format_korean_product_name(korean_name: str, product_type: str) -> str:
    if korean_name.endswith(product_type):
        return korean_name
    return _normalize_text(f"{korean_name} {product_type}")


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


if __name__ == "__main__":
    main()
