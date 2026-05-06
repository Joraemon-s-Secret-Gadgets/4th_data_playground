"""Search API helpers for Lush UK fragrance product discovery."""

from __future__ import annotations

import os
from typing import Any

import requests

from pipelines.common import build_request_headers, normalize_text


BASE_URL = "https://www.lush.com"
SEARCH_URL = f"{BASE_URL}/api/wyvern"
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


def fetch_collection_products(
    collection_name: str,
    *,
    session: requests.Session | None = None,
    per_page: int = 50,
) -> list[dict[str, str]]:
    """Fetch all pages for a Lush UK collection search."""
    active_session = session or requests.Session()
    rows: list[dict[str, str]] = []
    page = 1

    while page:
        payload = _fetch_search_page(active_session, collection_name, page, per_page)
        rows.extend(extract_search_products(payload))
        pagination = payload.get("data", {}).get("searchQuery", {}).get("pagination", {})
        page = int(pagination.get("nextPage") or 0)

    return dedupe_products(rows)


def extract_search_products(payload: dict[str, Any]) -> list[dict[str, str]]:
    """Extract normalized product rows from a Lush UK search payload."""
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
                "regular_price": format_gbp_price(content.get("minPrice"), str(content.get("currency") or "")),
                "image_url": extract_image_url(content),
            }
        )

    return products


def dedupe_products(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Deduplicate products by English name and product type."""
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (row["english_name"], row["product_type"])
        if key in seen:
            continue
        deduped.append(row)
        seen.add(key)
    return deduped


def format_gbp_price(value: Any, currency: str) -> str:
    """Format a raw GBP numeric value for output."""
    if value in (None, "") or currency != "GBP":
        return ""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return normalize_text(str(value))
    return f"£{amount:,.2f}"


def extract_image_url(content: dict[str, Any]) -> str:
    """Extract a product image URL from a Lush UK search payload item."""
    for key in ("thumbnail", "imageUrl", "image"):
        if image_url := normalize_image_url(content.get(key)):
            return image_url

    media = content.get("media")
    if isinstance(media, list):
        for item in media:
            if isinstance(item, dict) and (image_url := normalize_image_url(item.get("url") or item.get("src"))):
                return image_url
    return ""


def normalize_image_url(value: Any) -> str:
    """Normalize a Lush UK image URL value."""
    if not isinstance(value, str) or not value:
        return ""
    if value.startswith("//"):
        return f"https:{value}"
    if value.startswith("/"):
        return f"{BASE_URL}{value}"
    return value


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
        headers={"content-type": "application/json", **build_request_headers("LUSH_UK")},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(f"LUSH UK search API returned errors: {payload['errors']}")
    return payload

# End of file.
