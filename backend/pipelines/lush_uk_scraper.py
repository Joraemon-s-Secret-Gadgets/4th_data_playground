from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

import requests
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
SEARCH_URL = f"{BASE_URL}/api/wyvern"
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
    "Gift",
    "Glitter Mist Spray",
    "Lush Melt",
    "Scented Candle",
)
SEARCH_COLLECTION_NAMES = ("Fragrances",)
SEARCH_QUERY = """
query SearchQuery(
  $language: LushLanguageCodeEnum!,
  $client: LushClientEnum!,
  $sort: SortByInput!,
  $contentTypes: [SearchResultContentType!]!,
  $marketId: LushMarketCodeEnum!,
  $page: Int,
  $perPage: Int,
  $filters: [[String!]!],
  $mode: SearchModeEnum
) {
  searchQuery(
    language: $language,
    client: $client,
    sort: $sort,
    contentTypes: $contentTypes,
    marketID: $marketId,
    page: $page,
    perPage: $perPage,
    filters: $filters,
    mode: $mode
  ) {
    items {
      id
      content {
        ... on ProductPayload {
          id
          name
          slug
          minPrice
          maxPrice
          currency
          attributes {
            ... on StandardProductAttributes {
              type
              strapline
            }
          }
        }
      }
    }
    pagination {
      total
      page
      pages
      perPage
      nextPage
    }
  }
}
"""


def build_headers() -> dict[str, str]:
    return build_request_headers("LUSH_UK")


def fetch_category(
    url: str = DEFAULT_URL,
    *,
    use_selenium: bool | None = None,
    use_scrapling: bool | None = None,
) -> str:
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


def fetch_collection_products(
    collection_name: str,
    *,
    session: requests.Session | None = None,
    per_page: int = 50,
) -> list[dict[str, str]]:
    active_session = session or requests.Session()
    rows: list[dict[str, str]] = []
    page = 1

    while page:
        payload = _fetch_search_page(active_session, collection_name, page, per_page)
        rows.extend(extract_search_products(payload))
        pagination = payload.get("data", {}).get("searchQuery", {}).get("pagination", {})
        page = int(pagination.get("nextPage") or 0)

    return _dedupe_products(rows)


def extract_search_products(payload: dict[str, Any]) -> list[dict[str, str]]:
    items = payload.get("data", {}).get("searchQuery", {}).get("items", [])
    products: list[dict[str, str]] = []

    for item in items:
        content = item.get("content") if isinstance(item, dict) else None
        if not isinstance(content, dict):
            continue

        attributes = content.get("attributes") if isinstance(content.get("attributes"), dict) else {}
        product_type = normalize_text(str(attributes.get("type") or ""))
        if product_type not in PRODUCT_TYPES:
            continue

        name = normalize_text(str(content.get("name") or ""))
        slug = normalize_text(str(content.get("slug") or ""))
        if not name or not slug:
            continue

        products.append(
            {
                "country": "UK",
                "english_name": name,
                "product_type": product_type,
                "product_url": f"{BASE_URL}/uk/en/p/{slug.strip('/')}",
                "regular_price": _format_gbp_price(content.get("minPrice"), str(content.get("currency") or "")),
            }
        )

    return products


def fetch_product_price(product_url: str) -> str:
    if not product_url:
        return ""
    return extract_product_price(fetch_category(product_url))


def fetch_product_detail(product_url: str) -> dict[str, Any]:
    if not product_url:
        return {"ingredients": "", "key_ingredients": []}
    return extract_product_detail(fetch_category(product_url))


def extract_product_price(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for node in soup.select(".sr-only, button"):
        if price := _extract_sterling_price(node.get_text(" ", strip=True)):
            return price
    if price := _extract_next_data_price(soup):
        return price
    return _extract_sterling_price(soup.get_text(" ", strip=True))


def extract_product_detail(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data is None or next_data.string is None:
        return {"ingredients": "", "key_ingredients": []}

    payload = json.loads(next_data.string)
    apollo_state = payload.get("props", {}).get("pageProps", {}).get("__APOLLO_STATE__", {})
    product = next(
        (
            item
            for item in apollo_state.values()
            if isinstance(item, dict) and item.get("__typename") == "Product"
        ),
        None,
    )
    if not isinstance(product, dict):
        return {"ingredients": "", "key_ingredients": []}

    ingredients: list[str] = []
    key_ingredients: list[str] = []
    for attribute in product.get("attributes", []):
        if not isinstance(attribute, dict):
            continue
        slug = attribute.get("attribute", {}).get("slug")
        values = [
            normalize_text(str(value.get("name") or ""))
            for value in attribute.get("values", [])
            if isinstance(value, dict) and normalize_text(str(value.get("name") or ""))
        ]
        if slug == "ingredients":
            ingredients = values
        elif slug in {"key_ingredient", "key_ingredients"}:
            key_ingredients.extend(value for value in values if value not in key_ingredients)

    return {"ingredients": ", ".join(ingredients), "key_ingredients": key_ingredients}


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
    output_path = Path(os.getenv("LUSH_UK_OUTPUT_PATH", "data/lush_uk_fragrance_data.json"))
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


def _selected_fetcher() -> str:
    return os.getenv("LUSH_UK_FETCHER", "scrapling").strip().lower()


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


def _fetch_search_page(
    session: requests.Session,
    collection_name: str,
    page: int,
    per_page: int,
) -> dict[str, Any]:
    variables = {
        "language": os.getenv("LUSH_UK_SEARCH_LANGUAGE", "EN"),
        "client": "COMMERCE_WEB",
        "sort": {"field": "RELEVANCE", "value": "DESC"},
        "contentTypes": ["PRODUCT"],
        "marketId": os.getenv("LUSH_UK_SEARCH_MARKET_ID", "UK"),
        "page": page,
        "perPage": per_page,
        "filters": [[f"collections:{collection_name}"]],
        "mode": "KEYWORD",
    }
    response = session.post(
        SEARCH_URL,
        json={"operationName": "SearchQuery", "query": SEARCH_QUERY, "variables": variables},
        headers={"content-type": "application/json", **build_headers()},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(f"LUSH UK search API returned errors: {payload['errors']}")
    return payload


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
                "ingredients": str(detail.get("ingredients") or ""),
                "key_ingredients": detail.get("key_ingredients") or [],
            }
        )
    return detailed_rows


def _format_gbp_price(value: Any, currency: str) -> str:
    if value in (None, "") or currency != "GBP":
        return ""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return normalize_text(str(value))
    return f"£{amount:,.2f}"


def _extract_sterling_price(text: str) -> str:
    if match := re.search(r"£\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?", text):
        return match.group(0).replace("£ ", "£")
    return ""


def _extract_next_data_price(soup: BeautifulSoup) -> str:
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data is None or next_data.string is None:
        return ""

    payload = json.loads(next_data.string)
    apollo_state = payload.get("props", {}).get("pageProps", {}).get("__APOLLO_STATE__", {})
    amounts: list[tuple[float, int]] = []
    for item in apollo_state.values():
        if not isinstance(item, dict) or item.get("__typename") != "ProductVariant":
            continue

        for key, pricing in item.items():
            if not key.startswith("pricing") or not isinstance(pricing, dict):
                continue
            gross = pricing.get("price", {}).get("gross", {})
            if not isinstance(gross, dict) or gross.get("currency") != "GBP":
                continue
            amount = gross.get("amount")
            fraction_digits = int(gross.get("fractionDigits") or 2)
            if isinstance(amount, (int, float)):
                amounts.append((float(amount), fraction_digits))

    if not amounts:
        return ""

    amount, fraction_digits = min(amounts, key=lambda pair: pair[0])
    return f"£{amount:,.{fraction_digits}f}"


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
