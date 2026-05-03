from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from pipelines.lush_common import (
    build_request_headers,
    fetch_rendered_html,
    get_with_retries,
    normalize_text,
    print_json_rows,
)


DEFAULT_URL = "https://www.lush.com/uk/en/c/fragrances"
BASE_URL = "https://www.lush.com"
FALLBACK_COLLECTION_URLS = (
    "https://www.lush.com/uk/en/c/cruelty-free-perfume",
    "https://www.lush.com/uk/en/c/body-sprays",
    "https://www.lush.com/uk/en/c/solid-perfume",
    "https://www.lush.com/uk/en/c/perfume-gifts",
)
PRODUCT_TYPES = (
    "Solid Perfume",
    "Body Spray",
    "Perfume Gift Set",
    "Perfume",
    "Wash Card",
    "Candle",
    "Home Fragrance",
)


def build_headers() -> dict[str, str]:
    return build_request_headers("LUSH_UK")


def fetch_category(url: str = DEFAULT_URL, *, use_selenium: bool | None = None) -> str:
    if use_selenium is None:
        use_selenium = _env_flag("LUSH_UK_USE_SELENIUM")
    if use_selenium:
        return fetch_rendered_html(url)

    response = get_with_retries(url, headers=build_headers(), timeout=20)
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.text


def scrape_perfume_names(url: str = DEFAULT_URL) -> list[dict[str, str]]:
    rows = scrape_perfume_names_from_html(fetch_category(url))
    if rows or url != DEFAULT_URL:
        return rows

    for collection_url in FALLBACK_COLLECTION_URLS:
        rows.extend(scrape_perfume_names_from_html(fetch_category(collection_url)))
    return _dedupe_products(rows)


def scrape_perfume_names_from_html(html: str) -> list[dict[str, str]]:
    _raise_if_cloudflare_challenge(html)
    return [
        {
            "country": "UK",
            "english_name": product["english_name"],
            "product_type": product["product_type"],
            "product_url": product["product_url"],
        }
        for product in extract_fragrance_products(html)
    ]


def extract_fragrance_products(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    products: list[dict[str, str]] = []
    seen: set[str] = set()

    for link in soup.select('a[href*="/uk/en/p/"]'):
        product_url = _normalize_product_url(link["href"])
        if product_url in seen:
            continue

        card_text = _product_card_text(link)
        product_type = _infer_product_type(card_text, product_url)
        if not product_type:
            continue
        english_name = _infer_product_name(card_text, product_type, product_url)
        if not english_name:
            continue

        products.append(
            {
                "english_name": english_name,
                "product_type": product_type,
                "product_url": product_url,
            }
        )
        seen.add(product_url)

    return products or extract_referenced_products(html)


def extract_referenced_products(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data is None or next_data.string is None:
        return []

    payload = json.loads(next_data.string)
    apollo_state = payload.get("props", {}).get("pageProps", {}).get("__APOLLO_STATE__", {})
    products: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for item in apollo_state.values():
        if not isinstance(item, dict) or item.get("__typename") != "AttributeValue":
            continue
        if not str(item.get("reference") or "").startswith("UHJvZHVjdD"):
            continue

        product_type = _infer_referenced_product_type(str(item.get("slug") or ""))
        if not product_type:
            continue

        english_name = normalize_text(str(item.get("name") or ""))
        if not english_name:
            continue

        key = (english_name, product_type)
        if key in seen:
            continue
        products.append(
            {
                "english_name": english_name,
                "product_type": product_type,
                "product_url": _build_product_url(english_name, product_type),
            }
        )
        seen.add(key)

    return products


def main() -> None:
    url = os.getenv("LUSH_UK_HOME_URL", DEFAULT_URL)
    output_path = Path(os.getenv("LUSH_UK_OUTPUT_PATH", "data/lush_uk_perfume_names.json"))
    rows = scrape_perfume_names(url)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print_json_rows(rows)


def _raise_if_cloudflare_challenge(html: str) -> None:
    lowered = html.lower()
    if (
        ("just a moment" in lowered and "enable javascript and cookies" in lowered)
        or "잠시만 기다리십시오" in html
        or "challenges.cloudflare.com" in lowered
    ):
        raise RuntimeError(
            "LUSH UK returned a Cloudflare challenge page. "
            "Run with browser-backed crawling or provide valid request headers/cookies."
        )


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _normalize_product_url(raw_url: str) -> str:
    absolute_url = urljoin(BASE_URL, raw_url)
    url_without_fragment = urldefrag(absolute_url).url
    parts = urlsplit(url_without_fragment)
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def _build_product_url(english_name: str, product_type: str) -> str:
    slug = _slugify_product_name(english_name)
    if product_type == "Body Spray":
        slug = f"{slug}-body-spray"
    elif product_type == "Solid Perfume":
        slug = f"{slug}-solidperfume"
    elif product_type == "Perfume" and english_name != "29 High Street":
        slug = f"{slug}-perfume"
    return f"{BASE_URL}/uk/en/p/{slug}"


def _infer_referenced_product_type(attribute_slug: str) -> str:
    prefix = attribute_slug.split("_", 1)[0]
    return {
        "123": "Perfume",
        "1126": "Body Spray",
        "124": "Solid Perfume",
    }.get(prefix, "")


def _slugify_product_name(name: str) -> str:
    slug = normalize_text(name).lower()
    slug = slug.replace(":", "")
    slug = re.sub(r"['’]", "", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug


def _product_card_text(link: Any) -> str:
    card = link.find_parent(["article", "li"]) or link
    return normalize_text(" ".join(card.stripped_strings))


def _dedupe_products(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (row["english_name"], row["product_type"])
        if key in seen:
            continue
        deduped.append(row)
        seen.add(key)
    return deduped


def _infer_product_type(card_text: str, product_url: str) -> str:
    for product_type in PRODUCT_TYPES:
        if product_type in card_text:
            return product_type

    slug = product_url.rstrip("/").split("/")[-1]
    for product_type in PRODUCT_TYPES:
        if product_type.lower().replace(" ", "") in slug.replace("-", ""):
            return product_type
    return ""


def _infer_product_name(card_text: str, product_type: str, product_url: str) -> str:
    if card_text and product_type and product_type in card_text:
        name = normalize_text(card_text.split(product_type, 1)[0])
        if name:
            return name

    slug = product_url.rstrip("/").split("/")[-1]
    for suffix in ("-solidperfume", "-body-spray", "-perfume", "-wash-card", "-candle"):
        if slug.endswith(suffix):
            slug = slug[: -len(suffix)]
            break
    return normalize_text(slug.replace("-", " ").title())


if __name__ == "__main__":
    main()
