"""Tom Ford, Diptyque 같은 retail crawler 문서를 공통 스키마로 변환합니다."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipelines.common.normalized_schema import normalize_product_row
from pipelines.retail_exports import format_price


@dataclass(frozen=True)
class BrandConfig:
    """retail fragrance source 하나의 크롤링 설정입니다."""

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
    """retail crawler product 문서를 최종 향수 JSON row로 변환합니다.

    retail export에는 원천 사이트가 명시한 accords/keywords가 없을 수 있으므로,
    노트 이름만 최종 `notes`로 넘기고 향조/키워드는 자동 생성하지 않습니다.
    """
    source_country = str(product.get("country") or "")
    brand = str(product.get("brand_name") or "")
    return normalize_product_row(
        {
            "country": source_country,
            "brand": brand,
            "korean_name": str(product.get("product_name_ko") or ""),
            "english_name": str(product.get("product_name_original") or ""),
            "product_type": str(product.get("product_type") or ""),
            "product_url": str(product.get("source_url") or ""),
            "regular_price": format_price(_number_or_none(product.get("price_original")), str(product.get("currency") or "")),
            "image_url": _primary_image_url(product.get("images")),
            "ingredients": str(product.get("ingredients_ko") or ""),
            "key_ingredients": _key_ingredients(product.get("notes")),
        },
        source="official",
        source_country=source_country,
        brand=brand,
    )


def _primary_image_url(images: object) -> str:
    """이미지 배열에서 대표 원본 URL 하나를 고릅니다."""
    if not isinstance(images, list) or not images:
        return ""
    first = images[0]
    if isinstance(first, dict):
        return str(first.get("image_original_url") or "")
    return ""


def _key_ingredients(notes: object) -> list[str]:
    """retail notes 중 top/heart/base/key 우선순위로 대표 노트를 고릅니다."""
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
    """숫자로 바꿀 수 없는 가격 값은 None으로 정리합니다."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

# End of file.
