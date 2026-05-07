"""Normalize scraper rows into the public fragrance data contract."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from pipelines.common.translation import DeepLTranslator, Translator


SOURCE_VALUES = {"official", "fragrantica", "fraganty", "retail"}
CURRENCY_BY_SYMBOL = {"₩": "KRW", "원": "KRW", "$": "USD", "€": "EUR", "£": "GBP"}
ACCORD_KEYWORDS = {
    "aromatic": ["라벤더", "허브", "허벌", "민트", "스피어민트", "로즈마리", "세이지", "basil", "lavender", "mint", "sage", "aromatic"],
    "floral": ["로즈", "장미", "자스민", "라벤더", "바이올렛", "플로럴", "튜베로즈", "릴리", "violet", "rose", "jasmine", "floral"],
    "woody": ["우드", "샌달우드", "시더", "패출리", "베티버", "나무", "wood", "cedar", "sandalwood", "patchouli", "vetiver", "woody"],
    "fresh": ["상쾌", "프레쉬", "청량", "민트", "시트러스", "베르가못", "레몬", "fresh", "bergamot", "lemon", "citrus"],
    "green": ["그린", "허브", "풀", "잎", "민트", "fig", "tea", "green", "leaf"],
    "citrus": ["시트러스", "베르가못", "레몬", "오렌지", "자몽", "만다린", "라임", "bergamot", "lemon", "orange", "grapefruit", "lime", "citrus"],
    "musky": ["머스크", "암브레트", "musk", "ambrette", "musky"],
    "amber": ["앰버", "암브록산", "amber", "ambroxan"],
    "sweet": ["달콤", "바닐라", "꿀", "카라멜", "sweet", "vanilla", "honey", "caramel"],
    "spicy": ["스파이시", "페퍼", "후추", "카다멈", "시나몬", "pepper", "cardamom", "cinnamon", "spicy"],
    "powdery": ["파우더", "아이리스", "오리스", "powder", "iris", "orris", "powdery"],
    "incense": ["인센스", "프랑킨센스", "나그참파", "incense", "frankincense"],
    "aquatic": ["아쿠아", "마린", "바다", "물", "비", "aquatic", "marine", "water"],
}
KEYWORDS_BY_ACCORD = {
    "aromatic": "아로마틱한",
    "floral": "화사한",
    "woody": "차분한",
    "fresh": "상쾌한",
    "green": "싱그러운",
    "citrus": "상큼한",
    "musky": "포근한",
    "amber": "따뜻한",
    "sweet": "달콤한",
    "spicy": "개성있는",
    "powdery": "부드러운",
    "incense": "명상적인",
    "aquatic": "청량한",
}


def normalize_product_rows(
    rows: list[dict[str, Any]],
    *,
    source: str,
    source_country: str,
    brand: str,
    translator: Translator | None = None,
    generate_description: bool = True,
) -> list[dict[str, Any]]:
    """Normalize multiple scraper rows to the public fragrance schema."""
    selected_translator = translator if translator is not None else DeepLTranslator.from_env()
    return [
        normalize_product_row(
            row,
            source=source,
            source_country=source_country,
            brand=brand,
            translator=selected_translator,
            generate_description=generate_description,
        )
        for row in rows
    ]


def normalize_product_row(
    row: dict[str, Any],
    *,
    source: str,
    source_country: str,
    brand: str,
    translator: Translator | None = None,
    generate_description: bool = True,
) -> dict[str, Any]:
    """Normalize one legacy scraper row to the public fragrance schema."""
    original_country = str(row.get("country") or source_country or "")
    original_product_type = str(row.get("product_type") or "")
    english_name = str(row.get("english_name") or row.get("name") or "").strip()
    korean_name = str(row.get("korean_name") or "").strip()
    if not korean_name and english_name and translator is not None:
        korean_name = translator.translate(english_name)

    release_year = _release_year(row)
    notes = _notes(row)
    accords = _accords(row)
    ko_keywords, en_keywords = _keywords(row)
    description = _description(
        row,
        release_year,
        korean_name=korean_name,
        english_name=english_name,
        notes=notes,
        accords=accords,
        ko_keywords=ko_keywords,
        generate_description=generate_description,
    )

    price = parse_price(_price_value(row))
    meta = {
        "release_year": release_year,
        "original_product_type": original_product_type,
        "original_country": original_country,
    }
    if not price["raw"] and price["amount"] is None:
        meta["price_missing_reason"] = "source_unavailable"

    return {
        "source": source if source in SOURCE_VALUES else source,
        "source_country": source_country or original_country,
        "brand": str(row.get("brand") or brand or "").upper(),
        "korean_name": korean_name,
        "english_name": english_name,
        "normalized_name": normalize_name(english_name or korean_name),
        "product_type": "perfume",
        "product_subtype": normalize_product_subtype(original_product_type),
        "product_url": str(row.get("product_url") or row.get("url") or ""),
        "image_url": str(row.get("image_url") or ""),
        "price": price,
        "description": description,
        "ingredients_raw": str(row.get("ingredients_raw") or row.get("ingredients") or ""),
        "notes": notes,
        "accords": accords,
        "keywords": {"ko": ko_keywords, "en": en_keywords},
        "meta": meta,
    }


def parse_price(raw_value: object) -> dict[str, Any]:
    """Parse display price text into raw, numeric amount, and currency."""
    if isinstance(raw_value, dict):
        raw = str(raw_value.get("raw") or raw_value.get("display") or raw_value.get("regular_price") or "").strip()
        amount = raw_value.get("amount")
        currency = str(raw_value.get("currency") or "")
        parsed = parse_price(raw or amount or "")
        return {
            "raw": raw or parsed["raw"],
            "amount": amount if amount is not None else parsed["amount"],
            "currency": currency or parsed["currency"],
        }
    if isinstance(raw_value, (int, float)) and raw_value > 0:
        amount = int(raw_value) if float(raw_value).is_integer() else raw_value
        return {"raw": str(amount), "amount": amount, "currency": ""}

    raw = str(raw_value or "").strip()
    currency = ""
    for marker, code in CURRENCY_BY_SYMBOL.items():
        if marker in raw:
            currency = code
            break

    match = re.search(r"\d[\d,.\s]*", raw)
    if match is None:
        return {"raw": raw, "amount": None, "currency": currency}

    numeric = match.group(0).strip().replace(" ", "")
    if "," in numeric and "." not in numeric:
        amount_text = numeric.replace(",", "")
    elif "," in numeric and "." in numeric:
        amount_text = numeric.replace(",", "")
    else:
        amount_text = numeric

    try:
        amount_float = float(amount_text)
    except ValueError:
        amount: int | float | None = None
    else:
        amount = int(amount_float) if amount_float.is_integer() else amount_float

    return {"raw": raw, "amount": amount, "currency": currency}


def normalize_name(value: str) -> str:
    """Normalize product names for matching across sources."""
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    lowered = ascii_value.lower()
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def normalize_product_subtype(value: str) -> str:
    """Map source-specific product type labels to stable subtype values."""
    lowered = value.strip().lower()
    compact = lowered.replace("-", " ").replace("_", " ")
    mappings = [
        (("오 드 빠르펭", "오 드 퍼퓸", "오드퍼퓸", "eau de parfum", "edp"), "eau_de_parfum"),
        (("오 드 뚜왈렛", "오 드 투왈렛", "eau de toilette", "edt"), "eau_de_toilette"),
        (("코롱 인텐스", "cologne intense"), "cologne_intense"),
        (("코롱", "cologne"), "cologne"),
        (("인센스 스틱", "incense stick"), "incense_stick"),
        (("인센스", "incense"), "incense"),
        (("퍼퓸", "parfum", "fragrance", "향수", "perfume"), "perfume"),
        (("body spray",), "body_spray"),
        (("hair mist",), "hair_mist"),
        (("solid perfume",), "solid_perfume"),
    ]
    for needles, subtype in mappings:
        if any(needle in compact for needle in needles):
            return subtype
    return "perfume"


def _description(
    row: dict[str, Any],
    release_year: int | None,
    *,
    korean_name: str,
    english_name: str,
    notes: list[str],
    accords: list[str],
    ko_keywords: list[str],
    generate_description: bool,
) -> str:
    value = str(row.get("description") or "")
    ingredients = str(row.get("ingredients") or "")
    if value:
        return value
    if ingredients.startswith("Released in"):
        return ingredients
    if not generate_description:
        return ""
    return generate_fallback_description(
        korean_name=korean_name,
        english_name=english_name,
        notes=notes,
        accords=accords,
        ko_keywords=ko_keywords,
        release_year=release_year,
    )


def generate_fallback_description(
    *,
    korean_name: str,
    english_name: str,
    notes: list[str],
    accords: list[str],
    ko_keywords: list[str],
    release_year: int | None = None,
) -> str:
    """Build a concise description from normalized fields when source prose is absent."""
    display_name = korean_name or english_name
    if not display_name:
        return ""

    sentences: list[str] = []
    prefix = f"{display_name}은"
    if notes:
        note_text = ", ".join(notes[:5])
        if accords:
            accord_text = ", ".join(accords[:3])
            sentences.append(f"{prefix} {note_text} 노트가 중심이며 {accord_text} 분위기를 가진 향수입니다.")
        else:
            sentences.append(f"{prefix} {note_text} 노트가 중심인 향수입니다.")
    elif ko_keywords:
        keyword_text = ", ".join(ko_keywords[:4])
        sentences.append(f"{prefix} {keyword_text} 이미지의 향수입니다.")
    elif accords:
        accord_text = ", ".join(accords[:4])
        sentences.append(f"{prefix} {accord_text} 분위기를 가진 향수입니다.")
    elif release_year:
        sentences.append(f"{prefix} {release_year}년에 출시된 향수입니다.")
    else:
        sentences.append(f"{display_name} 향수입니다.")

    return " ".join(sentences)


def _notes(row: dict[str, Any]) -> list[str]:
    raw_notes = row.get("notes")
    if isinstance(raw_notes, dict):
        values: list[str] = []
        for key in ("Top", "Heart", "Base", "top", "middle", "heart", "base"):
            item = raw_notes.get(key, [])
            if isinstance(item, list):
                values.extend(str(value) for value in item)
        return _unique(values)
    if isinstance(raw_notes, list):
        return _unique(str(value) for value in raw_notes)
    return _unique(str(value) for value in row.get("key_ingredients", []) if isinstance(row.get("key_ingredients"), list))


def _accords(row: dict[str, Any]) -> list[str]:
    raw = row.get("accords", row.get("main_accords", []))
    if isinstance(raw, list):
        values = []
        for item in raw:
            if isinstance(item, dict):
                values.append(str(item.get("accord") or ""))
            else:
                values.append(str(item))
        return _unique(values)
    return []


def _keywords(row: dict[str, Any]) -> tuple[list[str], list[str]]:
    keywords = row.get("keywords")
    if isinstance(keywords, dict):
        return _unique(str(value) for value in keywords.get("ko", [])), _unique(str(value) for value in keywords.get("en", []))

    ko_values = row.get("ko_keywords", [])
    en_values = row.get("en_keywords", [])
    return (
        _unique(str(value) for value in ko_values) if isinstance(ko_values, list) else [],
        _unique(str(value) for value in en_values) if isinstance(en_values, list) else [],
    )


def _price_value(row: dict[str, Any]) -> object:
    for key in ("regular_price", "price", "price_text", "price_raw", "sale_price", "salePrice", "list_price"):
        value = row.get(key)
        if value not in (None, "", 0, "0"):
            return value
    return ""


def infer_accords(row: dict[str, Any], notes: list[str]) -> list[str]:
    """Infer accords from notes, description, ingredients, and existing Korean keywords."""
    keyword_values: list[str] = []
    keywords = row.get("keywords")
    if isinstance(keywords, dict):
        keyword_values.extend(str(value) for value in keywords.get("ko", []))
        keyword_values.extend(str(value) for value in keywords.get("en", []))

    haystack = " ".join(
        [
            " ".join(notes),
            str(row.get("description") or ""),
            str(row.get("ingredients") or row.get("ingredients_raw") or ""),
            " ".join(keyword_values),
        ]
    ).lower()

    inferred: list[str] = []
    for accord, needles in ACCORD_KEYWORDS.items():
        if any(needle.lower() in haystack for needle in needles):
            inferred.append(accord)
    if inferred:
        return inferred

    subtype = normalize_product_subtype(str(row.get("product_subtype") or row.get("product_type") or ""))
    if subtype in {"incense_stick", "incense"}:
        return ["incense"]
    if subtype in {"perfume", "eau_de_parfum", "eau_de_toilette", "cologne", "cologne_intense"}:
        return ["aromatic"]
    return []


def infer_ko_keywords(accords: list[str], row: dict[str, Any], notes: list[str]) -> list[str]:
    """Infer Korean mood keywords from accords, then fall back to source keywords."""
    values = [KEYWORDS_BY_ACCORD[accord] for accord in accords if accord in KEYWORDS_BY_ACCORD]
    if values:
        return _unique(values)

    keywords = row.get("keywords")
    if isinstance(keywords, dict):
        return _unique(str(value) for value in keywords.get("ko", []))
    return []


def _release_year(row: dict[str, Any]) -> int | None:
    value = row.get("release_year")
    if value is None:
        meta = row.get("meta")
        if isinstance(meta, dict):
            value = meta.get("release_year")
    try:
        year = int(str(value))
    except (TypeError, ValueError):
        ingredients = str(row.get("ingredients") or "")
        match = re.search(r"\b(19\d{2}|20\d{2})\b", ingredients)
        return int(match.group(1)) if match else None
    return year


def _unique(values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result

# End of file.
