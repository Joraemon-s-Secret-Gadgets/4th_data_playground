"""Search API helpers for matching Lush Korea product metadata."""

from __future__ import annotations

from typing import Any, Callable

import requests

from pipelines.common import normalize_text, strip_tags


def find_product_metadata(
    session: requests.Session,
    korean_name: str,
    product_type: str,
    *,
    search_url: str,
    base_url: str,
    get_with_retries: Callable[..., requests.Response],
) -> dict[str, str]:
    """Find English name, canonical URL, and price for a Korean product."""
    for query in (f"{korean_name} {product_type}", korean_name):
        try:
            response = get_with_retries(session, search_url, params={"query": query}, timeout=20)
            response.raise_for_status()
        except requests.RequestException:
            continue
        response.encoding = "utf-8"

        items = response.json().get("info", {}).get("item", [])
        if match := select_search_result(items, korean_name, product_type):
            item_code = str(match.get("itemUserCode") or match.get("itemCode") or "")
            return {
                "english_name": normalize_text(str(match.get("itemEName") or "")),
                "product_url": f"{base_url}/products/view/{item_code}" if item_code else "",
                "regular_price": format_krw_price(match.get("salePrice")),
            }

    return {"english_name": "", "product_url": "", "regular_price": ""}


def select_search_result(
    items: list[dict[str, Any]],
    korean_name: str,
    product_type: str,
) -> dict[str, Any] | None:
    """Select the best matching Lush Korea search result."""
    scored: list[tuple[int, dict[str, Any]]] = []
    target_full_name = normalize_text(f"{korean_name} {product_type}")

    for item in items:
        item_name = strip_tags(str(item.get("itemName") or item.get("highlightItemName") or ""))
        item_range = normalize_text(str(item.get("itemRange") or ""))
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


def format_krw_price(value: Any) -> str:
    """Format a raw KRW numeric value for output."""
    if value in (None, ""):
        return ""
    try:
        return f"{int(value):,}원"
    except (TypeError, ValueError):
        return normalize_text(str(value))

# End of file.
