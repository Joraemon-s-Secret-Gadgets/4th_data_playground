"""Product detail parsers for Jo Malone Korea product pages."""

from __future__ import annotations

import json
from typing import Any

from bs4 import BeautifulSoup

from pipelines.common import normalize_text
from pipelines.jomalone_korea.category import format_price_krw, infer_product_type, normalize_asset_url


def extract_product_detail(html: str, preferred_size: str = "") -> dict[str, Any]:
    """Extract normalized Jo Malone Korea product detail fields."""
    soup = BeautifulSoup(html, "html.parser")
    product_group = extract_product_group(soup)
    variant = select_variant(product_group, preferred_size)

    english_name = normalize_text(str(product_group.get("name") or ""))
    korean_name = extract_korean_name(soup)
    image_url = normalize_asset_url(str(variant.get("image") or product_group.get("image") or ""))
    description = extract_overview(soup) or normalize_text(str(product_group.get("description") or ""))

    return {
        "korean_name": korean_name,
        "english_name": english_name,
        "product_type": infer_product_type(english_name, str(product_group.get("url") or "")),
        "regular_price": extract_variant_price(variant),
        "image_url": image_url,
        "ingredients": description,
        "key_ingredients": extract_tasting_notes(soup),
    }


def extract_product_group(soup: BeautifulSoup) -> dict[str, Any]:
    """Read the Schema.org ProductGroup JSON-LD block."""
    for script in soup.select('script[type="application/ld+json"]'):
        if not script.string:
            continue
        payload = json.loads(script.string)
        if isinstance(payload, dict) and payload.get("@type") in {"ProductGroup", "Product"}:
            return payload
    return {}


def select_variant(product_group: dict[str, Any], preferred_size: str = "") -> dict[str, Any]:
    """Select the matching size variant from a ProductGroup."""
    variants = product_group.get("hasVariant")
    if not isinstance(variants, list):
        return product_group

    normalized_size = normalize_text(preferred_size).lower()
    if normalized_size:
        for variant in variants:
            if isinstance(variant, dict) and normalize_text(str(variant.get("size") or "")).lower() == normalized_size:
                return variant

    first_variant = next((variant for variant in variants if isinstance(variant, dict)), None)
    return first_variant or {}


def extract_variant_price(variant: dict[str, Any]) -> str:
    """Extract and format the KRW offer price for a selected variant."""
    offers = variant.get("offers")
    if isinstance(offers, list):
        offers = next((offer for offer in offers if isinstance(offer, dict)), None)
    if not isinstance(offers, dict):
        return ""
    if offers.get("priceCurrency") != "KRW":
        return ""
    return format_price_krw(offers.get("price"))


def extract_korean_name(soup: BeautifulSoup) -> str:
    """Extract the Korean product name from the page title."""
    if soup.title is None:
        return ""
    title = normalize_text(soup.title.get_text(" ", strip=True))
    return normalize_text(title.split("|", 1)[0])


def extract_overview(soup: BeautifulSoup) -> str:
    """Extract the product overview description."""
    if overview := soup.select_one(".elc-product-overview-no-accordion, .js-product-overview"):
        return normalize_text(overview.get_text(" ", strip=True))
    return ""


def extract_tasting_notes(soup: BeautifulSoup) -> list[str]:
    """Extract tasting note names from the product page."""
    notes: list[str] = []
    for note in soup.select(".tasting-notes__content-header"):
        value = normalize_text(note.get_text(" ", strip=True))
        if value and value not in notes:
            notes.append(value)
    return notes

# End of file.
