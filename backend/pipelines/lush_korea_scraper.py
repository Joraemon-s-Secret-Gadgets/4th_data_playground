from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from pipelines.lush_common import (
    build_request_headers,
    extract_product_remote_id as _extract_product_remote_id,
    get_with_retries as _get_with_retries,
    normalize_review as _normalize_review,
    normalize_text as _normalize_text,
    print_json_rows,
    strip_tags as _strip_tags,
)


DEFAULT_URL = "https://www.lush.co.kr/m/categories/index/56"
BASE_URL = "https://www.lush.co.kr"
SEARCH_URL = "https://www.lush.co.kr/m/elasticsearch/autolist"
VREVIEW_REVIEWS_URL = "https://one.vreview.tv/api/embed/v2/417377ee-f4a0-4d0d-8e48-0dc58f216fb9/reviews"
VREVIEW_REVIEW_EXPAND = (
    "rating,created_at,helpful_count,user_nickname,product,upload_from,"
    "spray_username,title,text,media_contents,comments"
)
PRODUCT_TYPES = {"보디 스프레이", "바디 스프레이", "퍼퓸", "솔리드 퍼퓸", "워시 카드", "캔들"}


def build_headers() -> dict[str, str]:
    return build_request_headers("LUSH_KR")


def extract_homepage_fragrance_products(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    if products := _extract_category_products(soup):
        return products

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
    response = _get_with_retries(url, headers=build_headers(), timeout=20)
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
        detail = fetch_product_detail(session, matched.get("product_url", ""))
        review_detail = fetch_product_reviews(session, matched.get("product_url", ""))
        rows.append(
            {
                "country": "KR",
                "korean_name": full_korean_name,
                "english_name": matched.get("english_name", ""),
                "product_type": product["product_type"],
                "product_url": matched.get("product_url", ""),
                "ingredients": detail["ingredients"],
                "key_ingredients": detail["key_ingredients"],
                "review_count": review_detail["review_count"],
                "reviews": review_detail["reviews"],
            }
        )
    return rows


def find_product_metadata(
    session: requests.Session,
    korean_name: str,
    product_type: str,
) -> dict[str, str]:
    for query in (f"{korean_name} {product_type}", korean_name):
        response = _get_with_retries(session, SEARCH_URL, params={"query": query}, timeout=20)
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


def fetch_product_detail(session: requests.Session, product_url: str) -> dict[str, Any]:
    if not product_url:
        return {"ingredients": "", "key_ingredients": []}

    response = _get_with_retries(session, product_url, timeout=20)
    response.raise_for_status()
    response.encoding = "utf-8"
    return extract_product_detail(response.text)


def fetch_product_reviews(session: requests.Session, product_url: str, limit: int = 100) -> dict[str, Any]:
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


def extract_product_detail(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    ingredient_section = _find_ingredient_section(soup)
    if ingredient_section is None:
        return {"ingredients": "", "key_ingredients": []}

    ingredients = ""
    for text_block in ingredient_section.select("p.text__main"):
        label = text_block.select_one(".theme__gray900")
        if label is None or "전 성분" not in _normalize_text(label.get_text(" ", strip=True)):
            continue

        value = text_block.select_one(".theme__gray800")
        if value is not None:
            ingredients = _normalize_text(value.get_text(" ", strip=True))
            break

    key_ingredients: list[str] = []
    seen: set[str] = set()
    for node in ingredient_section.select(".ingredient .ingredient__name"):
        name = _normalize_text(node.get_text(" ", strip=True))
        if name and name not in seen:
            key_ingredients.append(name)
            seen.add(name)

    return {"ingredients": ingredients, "key_ingredients": key_ingredients}


def main() -> None:
    url = os.getenv("LUSH_KR_HOME_URL", DEFAULT_URL)
    output_path = Path(os.getenv("LUSH_KR_OUTPUT_PATH", "data/lush_korea_perfume_names.json"))
    rows = scrape_perfume_names(url)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print_json_rows(rows)


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


def _extract_category_products(soup: BeautifulSoup) -> list[dict[str, str]]:
    products: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for item in soup.select("li.prdlist__item"):
        name_node = item.select_one(".prdlist__item__tit")
        type_node = item.select_one(".prdlist__item__category")
        if name_node is None or type_node is None:
            continue

        korean_name = _normalize_text(name_node.get_text(" ", strip=True))
        product_type = _normalize_text(type_node.get_text(" ", strip=True))
        if product_type not in PRODUCT_TYPES:
            continue

        key = (korean_name, product_type)
        if key in seen:
            continue
        products.append({"korean_name": korean_name, "product_type": product_type})
        seen.add(key)

    return products


def _find_ingredient_section(soup: BeautifulSoup) -> Any | None:
    heading = soup.find(string=lambda value: _normalize_text(value or "") == "INGREDIENT")
    if heading is None:
        return None

    heading_node = heading.parent
    if heading_node is None:
        return None
    return heading_node.find_parent("div", class_="primary__article")


def _format_korean_product_name(korean_name: str, product_type: str) -> str:
    if korean_name.endswith(product_type):
        return korean_name
    return _normalize_text(f"{korean_name} {product_type}")


if __name__ == "__main__":
    main()
