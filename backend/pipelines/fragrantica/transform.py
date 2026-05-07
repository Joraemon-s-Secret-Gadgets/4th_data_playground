"""Transform Fragrantica crawler exports into the local fragrance row schema."""

from __future__ import annotations

import re
from typing import Any

from pipelines.common.normalized_schema import normalize_product_row


COUNTRY_BY_BRAND = {
    "Giorgio Armani": "IT",
    "Maison Francis Kurkdjian": "FR",
}


def parse_semicolon_values(value: object) -> list[str]:
    """Split Fragrantica semicolon-delimited fields while preserving unique order."""
    if not isinstance(value, str):
        return []

    values: list[str] = []
    for part in value.split(";"):
        text = part.strip()
        if text and text not in values:
            values.append(text)
    return values


def format_fragrantica_rows(
    records: list[dict[str, Any]],
    *,
    source_url_template: str = "",
) -> list[dict[str, Any]]:
    """Convert Fragrantica source rows to the project JSON schema."""
    rows: list[dict[str, Any]] = []
    for item in records:
        brand = str(item.get("brand") or "")
        name = str(item.get("name") or "")
        release_year = str(item.get("release_year") or "")
        key_ingredients = (
            parse_semicolon_values(item.get("top_notes"))
            + parse_semicolon_values(item.get("middle_notes"))
            + parse_semicolon_values(item.get("base_notes"))
        )

        rows.append(
            normalize_product_row(
                {
                    "country": COUNTRY_BY_BRAND.get(brand, ""),
                    "brand": brand,
                    "korean_name": "",
                    "english_name": name,
                    "product_type": "향수",
                    "product_url": str(item.get("_url") or _build_source_url(brand, name, source_url_template)),
                    "regular_price": "",
                    "image_url": "",
                    "description": f"Released in {release_year}" if release_year else "",
                    "release_year": release_year,
                    "key_ingredients": _unique(key_ingredients),
                    "accords": parse_semicolon_values(item.get("accords")),
                },
                source="fragrantica",
                source_country=COUNTRY_BY_BRAND.get(brand, ""),
                brand=brand,
            )
        )
    return rows


def _build_source_url(brand: str, name: str, template: str) -> str:
    if not template:
        return ""
    return template.format(brand_slug=_slugify(brand), name_slug=_slugify(name))


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result

# End of file.
