"""Transform Fraganty raw and enriched records into local output rows."""

from __future__ import annotations

from typing import Any

from pipelines.fraganty.category import perfume_name_from_url


COUNTRY_BY_BRAND = {
    "Bvlgari": "이탈리아",
    "Chanel": "프랑스",
    "Dior": "프랑스",
}


def refine_raw_details(records: list[dict[str, Any]], *, require_review: bool = True) -> list[dict[str, Any]]:
    """Filter and normalize raw Fraganty detail records."""
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
    """Convert enriched Fraganty rows to the schema used by local JSON outputs."""
    english_by_url = {
        str(item.get("url") or ""): item for item in (english_rows or []) if isinstance(item, dict)
    }

    rows: list[dict[str, Any]] = []
    for item in korean_rows:
        url = str(item.get("url") or "")
        english_item = english_by_url.get(url, {})
        rows.append(
            {
                "country": COUNTRY_BY_BRAND.get(brand, ""),
                "korean_name": str(item.get("korean_name") or item.get("name") or ""),
                "english_name": str(english_item.get("name") or item.get("english_name") or item.get("name") or ""),
                "product_type": str(item.get("product_type") or "향수"),
                "product_url": url,
                "regular_price": extract_regular_price(item.get("price_info", item.get("regular_price", ""))),
                "image_url": str(item.get("image_url") or ""),
                "ingredients": str(item.get("ingredients") or ""),
                "key_ingredients": flatten_notes(item.get("notes", item.get("key_ingredients", []))),
                "keywords": normalize_accords(item.get("main_accords", item.get("keywords", []))),
                "ko_keywords": extract_keywords(item.get("ai_analysis"), language="ko"),
                "en_keywords": extract_keywords(english_item.get("ai_analysis") or item.get("ai_analysis"), language="en"),
            }
        )

    return rows


def normalize_accords(value: object) -> list[str]:
    """Normalize accords from raw dictionaries or already formatted strings."""
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
    """Reduce Fraganty percentage maps to high-signal season and time labels."""
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
    """Flatten Top/Heart/Base notes while preserving order and uniqueness."""
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
    """Extract a display price from Fraganty price fields."""
    if isinstance(value, dict):
        retail = value.get("retail", "")
        if isinstance(retail, list):
            return str(retail[0]) if retail else ""
        return str(retail) if retail else ""
    return str(value) if value else ""


def extract_keywords(analysis: object, *, language: str) -> list[str]:
    """Extract mood and occasion keywords from an AI analysis payload."""
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
    result: list[str] = []
    for value in values:
        text = str(value or "")
        if text and text not in result:
            result.append(text)
    return result

# End of file.
