"""Shared facade for retail-site fragrance crawlers such as Tom Ford and Diptyque."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipelines.retail_exports import format_price


@dataclass(frozen=True)
class BrandConfig:
    """Configuration for one retail fragrance source."""

    key: str
    brand_name: str
    source_site: str
    country: str
    start_urls: list[str]
    allowed_domains: tuple[str, ...]
    default_currency: str


BRAND_CONFIGS: dict[str, BrandConfig] = {
    "tomford": BrandConfig(
        key="tomford",
        brand_name="Tom Ford",
        source_site="tomford_beauty",
        country="US",
        start_urls=["https://www.tomfordbeauty.com/collections/fragrance"],
        allowed_domains=("tomfordbeauty.com",),
        default_currency="USD",
    ),
    "diptyque": BrandConfig(
        key="diptyque",
        brand_name="Diptyque",
        source_site="diptyque_emea",
        country="BE",
        start_urls=["https://emea.diptyqueparis.com/en-be/collections/all-fragrances"],
        allowed_domains=("diptyqueparis.com",),
        default_currency="EUR",
    ),
}


def product_to_local_row(product: dict[str, Any]) -> dict[str, Any]:
    """Convert a retail crawler product document to the local fragrance row schema."""
    return {
        "country": str(product.get("country") or ""),
        "korean_name": str(product.get("product_name_ko") or ""),
        "english_name": str(product.get("product_name_original") or ""),
        "product_type": str(product.get("product_type") or ""),
        "product_url": str(product.get("source_url") or ""),
        "regular_price": format_price(_number_or_none(product.get("price_original")), str(product.get("currency") or "")),
        "image_url": _primary_image_url(product.get("images")),
        "ingredients": str(product.get("ingredients_ko") or ""),
        "key_ingredients": _key_ingredients(product.get("notes")),
    }


def _primary_image_url(images: object) -> str:
    if not isinstance(images, list) or not images:
        return ""
    first = images[0]
    if isinstance(first, dict):
        return str(first.get("image_original_url") or "")
    return ""


def _key_ingredients(notes: object) -> list[str]:
    if not isinstance(notes, list):
        return []

    for note_type in ("top", "heart", "base", "key"):
        values: list[str] = []
        for note in notes:
            if not isinstance(note, dict) or note.get("note_type") != note_type:
                continue
            value = str(note.get("note_name_ko") or note.get("note_name_original") or "")
            if value and value not in values:
                values.append(value)
        if values:
            return values[:8]
    return []


def _number_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

# End of file.
