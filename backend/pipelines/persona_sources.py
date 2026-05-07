"""Persona-L crawler export를 프로젝트 공통 스키마로 변환합니다.

Persona-L 원본 데이터는 브랜드별로 가격, family, notes 표현이 조금씩 다릅니다.
이 모듈은 해당 차이를 정리한 뒤 `normalize_product_row`로 넘기는 어댑터입니다.
"""

from __future__ import annotations

import re
from typing import Any

from pipelines.common.normalized_schema import normalize_product_row


SOURCE_COUNTRY_BY_BRAND = {
    "Byredo": "KR",
    "Le Labo": "KR",
    "Nag Champa": "KR",
}


def format_persona_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Persona-L row 목록을 정규화된 향수 row 목록으로 변환합니다."""
    return [format_persona_row(row) for row in rows]


def format_persona_row(row: dict[str, Any]) -> dict[str, Any]:
    """Persona-L row 하나를 공통 향수 데이터 계약으로 변환합니다.

    Nag Champa의 `keywords`는 원본 크롤러 코드에서 상품명 기반으로 생성된 값이라
    사이트 원천 키워드로 보지 않습니다. 데이터 신뢰도 정책에 맞춰 저장하지 않습니다.
    """
    brand = str(row.get("brand") or "")
    source_country = SOURCE_COUNTRY_BY_BRAND.get(brand, "KR")
    product_type = str(row.get("category") or "향수")
    notes = parse_byredo_note_lines(row.get("notes", []))
    raw_keywords = row.get("keywords", [])
    if brand == "Nag Champa":
        raw_keywords = []

    return normalize_product_row(
        {
            "country": source_country,
            "brand": brand,
            "korean_name": str(row.get("name") or ""),
            "english_name": "",
            "product_type": product_type,
            "product_url": str(row.get("source_url") or ""),
            "regular_price": _format_price(row.get("price") or row.get("price_text") or row.get("regular_price")),
            "image_url": str(row.get("image_url") or ""),
            "description": str(row.get("description") or ""),
            "notes": notes,
            "accords": _accords_from_family(row.get("family")),
            "keywords": {"ko": [str(value) for value in raw_keywords] if isinstance(raw_keywords, list) else [], "en": []},
        },
        source="official",
        source_country=source_country,
        brand=brand,
    )


def parse_byredo_note_lines(note_lines: object) -> list[str]:
    """`탑 노트: 베르가못, 로즈` 같은 Persona-L 노트 문자열을 평탄화합니다."""
    if not isinstance(note_lines, list):
        return []

    notes: list[str] = []
    for line in note_lines:
        text = str(line or "").strip()
        if not text:
            continue
        if ":" in text:
            text = text.split(":", 1)[1]
        for part in re.split(r",|/|·", text):
            note = part.strip()
            if note and note not in notes:
                notes.append(note)
    return notes


def _accords_from_family(value: object) -> list[str]:
    """Persona-L의 `family` 값을 원천 향조로 보존합니다."""
    text = str(value or "").strip()
    return [text] if text else []


def _format_price(value: object) -> str:
    """숫자 또는 표시 문자열 가격을 KRW 중심 표시 가격으로 정리합니다."""
    if value in (None, "", 0, "0"):
        return ""
    if isinstance(value, str):
        text = value.strip()
        if not text or text == "0":
            return ""
        if any(marker in text for marker in ("₩", "원", "$", "€", "£")):
            return text
    try:
        amount = int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return str(value)
    if amount <= 0:
        return ""
    return f"{amount:,}원"

# End of file.
