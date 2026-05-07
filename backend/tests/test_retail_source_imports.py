"""Tests for refactored retail fragrance source import helpers."""

from pipelines.retail_exports import (
    format_price,
    is_probably_fragrance_product,
    load_jsonl_products,
    load_mysql_ready_products,
)
from pipelines.retail_multibrand_scraper import BRAND_CONFIGS, product_to_local_row


def test_load_mysql_ready_products_reads_products_array() -> None:
    payload = {
        "brands": [{"name": "Creed"}],
        "products": [
            {
                "country": "UK",
                "korean_name": "아벤투스",
                "english_name": "Aventus",
                "product_type": "Fragrance",
                "product_url": "https://www.creedfragrance.com/p/aventus/12870029/",
                "regular_price": "€330.00",
                "image_url": "https://static.thcdn.com/productimg/original/12870029.jpg",
                "ingredients": "알코올-향료",
                "key_ingredients": ["베르가못"],
            }
        ],
    }

    assert load_mysql_ready_products(payload) == payload["products"]


def test_load_jsonl_products_reads_nonempty_lines() -> None:
    raw = """
    {"country":"KR","korean_name":"아이노아 퍼퓸","english_name":"Ainoa","key_ingredients":["리날룰"]}

    {"country":"KR","korean_name":"누베 퍼퓸","english_name":"Nube","key_ingredients":[]}
    """

    assert [row["english_name"] for row in load_jsonl_products(raw)] == ["Ainoa", "Nube"]


def test_retail_export_helpers_format_prices_and_filter_non_fragrance() -> None:
    assert format_price(250, "USD") == "$250.00"
    assert format_price(None, "USD") == ""
    assert is_probably_fragrance_product("Oud Wood Eau de Parfum", "Eau de Parfum")
    assert not is_probably_fragrance_product("Eye Color Quad", "")


def test_retail_multibrand_facade_exposes_tomford_and_diptyque_configs() -> None:
    assert BRAND_CONFIGS["tomford"].start_urls == ["https://www.tomfordbeauty.com/collections/fragrance"]
    assert BRAND_CONFIGS["diptyque"].country == "BE"


def test_product_to_local_row_prefers_translated_note_names() -> None:
    row = product_to_local_row(
        {
            "country": "US",
            "brand_name": "Tom Ford",
            "product_name_original": "Oud Wood Eau de Parfum",
            "product_name_ko": "오드 우드 오 드 퍼퓸",
            "product_type": "Eau de Parfum",
            "source_url": "https://www.tomfordbeauty.com/products/oud-wood",
            "price_original": 250,
            "currency": "USD",
            "images": [{"image_original_url": "https://example.test/oud.jpg"}],
            "ingredients_ko": "알코올, 향료",
            "notes": [
                {"note_type": "top", "note_name_original": "Rosewood", "note_name_ko": "로즈우드"},
                {"note_type": "base", "note_name_original": "Oud", "note_name_ko": "우드"},
            ],
        }
    )

    assert row == {
        "source": "official",
        "source_country": "US",
        "brand": "TOM FORD",
        "korean_name": "오드 우드 오 드 퍼퓸",
        "english_name": "Oud Wood Eau de Parfum",
        "normalized_name": "oud wood eau de parfum",
        "product_type": "perfume",
        "product_subtype": "eau_de_parfum",
        "product_url": "https://www.tomfordbeauty.com/products/oud-wood",
        "image_url": "https://example.test/oud.jpg",
        "price": {"raw": "$250.00", "amount": 250, "currency": "USD"},
        "description": "오드 우드 오 드 퍼퓸은 로즈우드 노트가 중심인 향수입니다.",
        "ingredients_raw": "알코올, 향료",
        "notes": ["로즈우드"],
        "accords": [],
        "keywords": {"ko": [], "en": []},
        "meta": {
            "release_year": None,
            "original_product_type": "Eau de Parfum",
            "original_country": "US",
        },
    }
