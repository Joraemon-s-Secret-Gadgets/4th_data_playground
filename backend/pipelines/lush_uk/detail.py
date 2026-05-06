"""Product detail and price parsers for Lush UK product pages."""

from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup

from pipelines.common import normalize_text


def extract_product_price(html: str) -> str:
    """Extract the visible or embedded GBP price from a product page."""
    soup = BeautifulSoup(html, "html.parser")
    for node in soup.select(".sr-only, button"):
        if price := _extract_sterling_price(node.get_text(" ", strip=True)):
            return price
    if price := _extract_next_data_price(soup):
        return price
    return _extract_sterling_price(soup.get_text(" ", strip=True))


def extract_product_detail(html: str) -> dict[str, Any]:
    """Extract ingredient fields from Next.js Apollo product state."""
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

# End of file.
