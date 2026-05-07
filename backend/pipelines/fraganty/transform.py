"""Fraganty raw/enriched records를 공통 향수 데이터 계약으로 변환합니다."""

from __future__ import annotations

from typing import Any

from pipelines.common.normalized_schema import normalize_product_row

from pipelines.fraganty.category import perfume_name_from_url


COUNTRY_BY_BRAND = {
    "Bvlgari": "이탈리아",
    "Chanel": "프랑스",
    "Dior": "프랑스",
}


def refine_raw_details(records: list[dict[str, Any]], *, require_review: bool = True) -> list[dict[str, Any]]:
    """Fraganty 상세 raw record에서 성공/검토 완료 데이터만 추립니다."""
    refined: list[dict[str, Any]] = []
    for item in records:
        if str(item.get("status") or "").lower() != "success":
            continue

        if require_review and (item.get("first_impression") in {"", "N/A"} or item.get("scent_profile") in {"", "N/A"}):
            continue

        url = str(item.get("url") or "")
        normalized = dict(item)
        normalized["name"] = perfume_name_from_url(url) if url else str(item.get("name") or "unknown")
        normalized["main_accords"] = normalize_accords(item.get("main_accords", []))
        normalized["usage_stats"] = normalize_usage_stats(item.get("usage_stats", {}))
        refined.append(normalized)

    return refined


def format_final_rows(
    korean_rows: list[dict[str, Any]],
    *,
    english_rows: list[dict[str, Any]] | None = None,
    brand: str,
) -> list[dict[str, Any]]:
    """한국어/영어 Fraganty enriched row를 병합해 최종 JSON row로 변환합니다.

    Fraganty는 main accords와 AI 분석 키워드를 원천 export에 포함하므로,
    이 값들은 추론값이 아니라 소스 제공값으로 보고 보존합니다.
    """
    english_by_url = {
        str(item.get("url") or ""): item for item in (english_rows or []) if isinstance(item, dict)
    }

    rows: list[dict[str, Any]] = []
    for item in korean_rows:
        url = str(item.get("url") or "")
        english_item = english_by_url.get(url, {})
        rows.append(
            normalize_product_row(
                {
                    "country": COUNTRY_BY_BRAND.get(brand, ""),
                    "brand": brand,
                    "korean_name": str(item.get("korean_name") or item.get("name") or ""),
                    "english_name": str(english_item.get("name") or item.get("english_name") or item.get("name") or ""),
                    "product_type": str(item.get("product_type") or "향수"),
                    "product_url": url,
                    "regular_price": extract_regular_price(item.get("price_info", item.get("regular_price", ""))),
                    "image_url": str(item.get("image_url") or ""),
                    "ingredients": str(item.get("ingredients") or ""),
                    "key_ingredients": flatten_notes(item.get("notes", item.get("key_ingredients", []))),
                    "accords": normalize_accords(item.get("main_accords", item.get("keywords", []))),
                    "ko_keywords": extract_keywords(item.get("ai_analysis"), language="ko"),
                    "en_keywords": extract_keywords(english_item.get("ai_analysis") or item.get("ai_analysis"), language="en"),
                },
                source="fraganty",
                source_country=COUNTRY_BY_BRAND.get(brand, ""),
                brand=brand,
            )
        )

    return rows


def normalize_accords(value: object) -> list[str]:
    """dict 또는 문자열 배열로 들어온 Fraganty accords를 중복 없는 문자열 배열로 정리합니다."""
    if not isinstance(value, list):
        return []

    accords: list[str] = []
    for item in value:
        if isinstance(item, dict):
            text = str(item.get("accord") or "")
        else:
            text = str(item or "")
        if text and text not in accords:
            accords.append(text)
    return accords


def normalize_usage_stats(value: object) -> dict[str, object]:
    """Fraganty 사용 통계 중 신뢰도가 높은 계절/시간대 값만 축약합니다."""
    if not isinstance(value, dict):
        return {}

    normalized: dict[str, object] = {}
    if seasons := _percent_map(value.get("Season")):
        selected = [name for name, percent in seasons.items() if percent >= 70]
        normalized["Season"] = selected or [max(seasons, key=seasons.get)]

    if times := _percent_map(value.get("Time")):
        normalized["Time"] = max(times, key=times.get)

    return normalized


def flatten_notes(value: object) -> list[str]:
    """Top/Heart/Base 노트를 순서 보존 배열로 평탄화합니다."""
    if isinstance(value, list):
        return _unique_strings(value)
    if not isinstance(value, dict):
        return []

    notes: list[str] = []
    for category in ("Top", "Heart", "Base"):
        category_notes = value.get(category, [])
        if isinstance(category_notes, list):
            notes.extend(str(note) for note in category_notes)
    return _unique_strings(notes)


def extract_regular_price(value: object) -> str:
    """Fraganty 가격 payload에서 표시 가격 하나를 추출합니다."""
    if isinstance(value, dict):
        retail = value.get("retail", "")
        if isinstance(retail, list):
            return str(retail[0]) if retail else ""
        return str(retail) if retail else ""
    return str(value) if value else ""


def extract_keywords(analysis: object, *, language: str) -> list[str]:
    """Fraganty AI 분석 payload에서 mood/occasion 키워드를 추출합니다."""
    if not isinstance(analysis, dict):
        return []

    keywords: list[str] = []
    for field in ("moods", "occasions"):
        values = analysis.get(field, [])
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, dict):
                text = str(value.get(language) or "")
            else:
                text = str(value or "")
            if text:
                keywords.append(text)
    return _unique_strings(keywords)


def _percent_map(value: object) -> dict[str, int]:
    """`80%` 같은 문자열 퍼센트를 정수 dict로 변환합니다."""
    if not isinstance(value, dict):
        return {}

    percentages: dict[str, int] = {}
    for key, raw_value in value.items():
        try:
            percentages[str(key)] = int(str(raw_value).replace("%", "").strip())
        except ValueError:
            continue
    return percentages


def _unique_strings(values: list[object]) -> list[str]:
    """문자열 배열의 빈 값과 중복을 제거합니다."""
    result: list[str] = []
    for value in values:
        text = str(value or "")
        if text and text not in result:
            result.append(text)
    return result

# End of file.
