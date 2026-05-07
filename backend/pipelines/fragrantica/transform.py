"""Fragrantica crawler export를 공통 향수 데이터 계약으로 변환합니다."""

from __future__ import annotations

import re
from typing import Any

from pipelines.common.normalized_schema import normalize_product_row


COUNTRY_BY_BRAND = {
    "Giorgio Armani": "IT",
    "Maison Francis Kurkdjian": "FR",
}


def parse_semicolon_values(value: object) -> list[str]:
    """세미콜론으로 구분된 Fragrantica 필드를 순서 보존 배열로 나눕니다."""
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
    """Fragrantica source row 목록을 프로젝트 최종 JSON 스키마로 변환합니다.

    Fragrantica는 향조와 노트는 제공하지만 판매 가격은 제공하지 않습니다.
    따라서 가격은 빈 값으로 두고 정규화 계층에서 누락 사유를 기록합니다.
    """
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
    """브랜드/상품 slug 템플릿으로 Fragrantica URL을 만듭니다."""
    if not template:
        return ""
    return template.format(brand_slug=_slugify(brand), name_slug=_slugify(name))


def _slugify(value: str) -> str:
    """Fragrantica URL 조합에 사용할 간단한 slug를 만듭니다."""
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def _unique(values: list[str]) -> list[str]:
    """문자열 배열의 순서를 유지하며 중복을 제거합니다."""
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result

# End of file.
